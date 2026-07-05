// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Anki for LSAT: the "points at stake" review queue (the Rust engine change).
//!
//! A read-only ordering of due cards by **topic exam weight x student
//! weakness**, surfacing the single most valuable card to study first. Because
//! it lives in the shared Rust backend, it ships identically to the desktop app
//! and the AnkiDroid build.
//!
//! It is a *pure query*: it never mutates the collection, records no undo
//! entry, and runs outside the transaction/op framework, so it cannot corrupt
//! scheduling state.
//!
//! Scoring (tunable; mirrored in the model notes):
//!
//! ```text
//! mastery(card, tag) = RECALL_WEIGHT * recall + PERF_WEIGHT * perf_mastery(tag)
//! points(card)       = max over card.tags of weight(tag) * (1 - mastery(card, tag))
//! ```
//!
//! where `recall` is the card's current FSRS retrievability (0 when the card
//! has no FSRS memory state, i.e. maximum weakness), and
//! `weight`/`perf_mastery` come from the caller's LSAT taxonomy (passed per
//! request so the weights stay editable in one YAML file rather than hard-coded
//! in Rust).

use std::collections::HashMap;

use fsrs::FSRS;
use fsrs::FSRS5_DEFAULT_DECAY;

use crate::prelude::*;
use crate::scheduler::timing::SchedTimingToday;
use crate::search::JoinSearches;
use crate::search::SearchBuilder;
use crate::search::SearchNode;
use crate::search::StateKind;
use crate::tags::split_tags;

/// Relative contribution of FSRS recall vs. recent graded performance to the
/// blended mastery estimate. Sum to 1.0.
const RECALL_WEIGHT: f32 = 0.5;
const PERF_WEIGHT: f32 = 0.5;

pub struct PointsAtStakeEntry {
    pub card_id: CardId,
    pub points: f32,
    pub top_tag: String,
}

impl Collection {
    /// Order the due cards in `deck_id` (and its children; 0 = whole
    /// collection) by points at stake, highest first. Read-only.
    pub(crate) fn points_at_stake_queue(
        &mut self,
        deck_id: DeckId,
        limit: usize,
        topics: &[(String, f32, f32)],
    ) -> Result<Vec<PointsAtStakeEntry>> {
        let timing = self.timing_today()?;
        // tag -> (weight, perf_mastery)
        let weights: HashMap<&str, (f32, f32)> = topics
            .iter()
            .map(|(tag, weight, perf)| (tag.as_str(), (*weight, *perf)))
            .collect();
        // The retrievability model is parameter-free here, so construct it ONCE
        // rather than per card (a new FSRS per card was pure overhead across tens
        // of thousands of due cards).
        let fsrs = FSRS::new(None).unwrap();

        // Candidate set: cards that are due today (review/learning), optionally
        // restricted to a deck and its children. Gathered via the existing
        // search infrastructure so we reuse Anki's deck/due semantics verbatim.
        let search: SearchBuilder = if deck_id.0 != 0 {
            SearchNode::from_deck_id(deck_id, true).and(StateKind::Due)
        } else {
            StateKind::Due.into()
        };

        // Bulk-load every due card in ONE query, then every distinct note's tags
        // in ONE more query -- instead of a get_card + get_note round-trip per
        // card (~2xN SQL statements, the dominant cost on the 50k-card deck).
        let cards = self.all_cards_for_search(search)?;
        let mut note_ids: Vec<NoteId> = cards.iter().map(|c| c.note_id).collect();
        note_ids.sort_unstable();
        note_ids.dedup();
        let tags_by_note: HashMap<NoteId, String> = self
            .storage
            .get_note_tags_by_id_list(&note_ids)?
            .into_iter()
            .map(|nt| (nt.id, nt.tags))
            .collect();

        let mut entries: Vec<PointsAtStakeEntry> = Vec::with_capacity(cards.len());
        for card in &cards {
            let recall = card_recall(card, &timing, &fsrs);
            let tags_str = tags_by_note
                .get(&card.note_id)
                .map(String::as_str)
                .unwrap_or("");
            let card_tags: Vec<&str> = split_tags(tags_str).collect();
            let (points, top_tag) =
                best_points(&card_tags, recall, &weights).unwrap_or((0.0, String::new()));
            entries.push(PointsAtStakeEntry {
                card_id: card.id,
                points,
                top_tag,
            });
        }

        // Highest points first; deterministic tie-break by ascending card id.
        entries.sort_by(|a, b| {
            b.points
                .partial_cmp(&a.points)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| a.card_id.cmp(&b.card_id))
        });
        if limit > 0 {
            entries.truncate(limit);
        }
        Ok(entries)
    }
}

/// Current FSRS retrievability (recall probability, 0..1), computed on demand
/// from the card's stored memory state. Returns 0.0 when there is no FSRS state
/// (e.g. a review card whose parameters were never optimized) -- i.e. treat an
/// unknown card as maximally weak.
fn card_recall(card: &Card, timing: &SchedTimingToday, fsrs: &FSRS) -> f32 {
    card.memory_state
        .as_ref()
        .zip(card.seconds_since_last_review(timing))
        .map(|(state, seconds)| {
            fsrs.current_retrievability_seconds(
                (*state).into(),
                seconds,
                card.decay.unwrap_or(FSRS5_DEFAULT_DECAY),
            )
        })
        .unwrap_or(0.0)
}

/// The maximum `(points, tag)` over a card's tags, or `None` if none of its
/// tags have a configured weight. `points = weight * (1 - mastery)`.
fn best_points(
    tags: &[&str],
    recall: f32,
    weights: &HashMap<&str, (f32, f32)>,
) -> Option<(f32, String)> {
    let mut best: Option<(f32, String)> = None;
    for tag in tags {
        if let Some((weight, perf)) = weights.get(*tag) {
            let mastery = (RECALL_WEIGHT * recall + PERF_WEIGHT * perf).clamp(0.0, 1.0);
            let points = weight * (1.0 - mastery);
            let is_better = match &best {
                Some((best_points, _)) => points > *best_points,
                None => true,
            };
            if is_better {
                best = Some((points, (*tag).to_string()));
            }
        }
    }
    best
}

#[cfg(test)]
mod test {
    use super::*;
    use crate::card::CardQueue;
    use crate::card::CardType;
    use crate::card::FsrsMemoryState;
    use crate::tests::DeckAdder;
    use crate::tests::NoteAdder;
    use crate::timestamp::TimestampSecs;

    /// Add a due review card tagged with `tags` and no FSRS memory state, so
    /// recall is a deterministic 0.0 and mastery is driven purely by the
    /// per-topic `perf_mastery` we pass in the request.
    fn add_due_card(col: &mut Collection, tags: &[&str]) -> CardId {
        let mut note = NoteAdder::basic(col).fields(&["q", "a"]).note();
        note.tags = tags.iter().map(|t| t.to_string()).collect();
        col.add_note(&mut note, DeckId(1)).unwrap();
        let card_id = col.storage.card_ids_of_notes(&[note.id]).unwrap()[0];
        let mut card = col.storage.get_card(card_id).unwrap().unwrap();
        card.ctype = CardType::Review;
        card.queue = CardQueue::Review;
        card.due = 0;
        card.memory_state = None;
        col.storage.update_card(&card).unwrap();
        card_id
    }

    fn topics(items: &[(&str, f32, f32)]) -> Vec<(String, f32, f32)> {
        items
            .iter()
            .map(|(tag, weight, perf)| (tag.to_string(), *weight, *perf))
            .collect()
    }

    #[test]
    fn orders_by_topic_weight_when_weakness_equal() {
        let mut col = Collection::new();
        let high = add_due_card(&mut col, &["lsat::lr::weaken"]);
        let low = add_due_card(&mut col, &["lsat::lr::evaluate"]);
        let t = topics(&[
            ("lsat::lr::weaken", 0.9, 0.0),
            ("lsat::lr::evaluate", 0.1, 0.0),
        ]);

        let q = col.points_at_stake_queue(DeckId(0), 0, &t).unwrap();

        assert_eq!(q.len(), 2);
        assert_eq!(
            q[0].card_id, high,
            "higher exam-weight topic should rank first"
        );
        assert_eq!(q[1].card_id, low);
        assert!(q[0].points > q[1].points);
        assert_eq!(q[0].top_tag, "lsat::lr::weaken");
    }

    #[test]
    fn orders_by_weakness_when_weight_equal() {
        let mut col = Collection::new();
        // Equal weight; the weaker topic (lower perf_mastery) should rank first.
        let strong = add_due_card(&mut col, &["lsat::lr::strengthen"]);
        let weak = add_due_card(&mut col, &["lsat::lr::weaken"]);
        let t = topics(&[
            ("lsat::lr::strengthen", 0.5, 0.9),
            ("lsat::lr::weaken", 0.5, 0.1),
        ]);

        let q = col.points_at_stake_queue(DeckId(0), 0, &t).unwrap();

        assert_eq!(q.len(), 2);
        assert_eq!(
            q[0].card_id, weak,
            "weaker topic should rank first at equal weight"
        );
        assert_eq!(q[1].card_id, strong);
        assert!(q[0].points > q[1].points);
    }

    #[test]
    fn respects_limit_and_ignores_unweighted_tags() {
        let mut col = Collection::new();
        add_due_card(&mut col, &["lsat::lr::weaken"]);
        add_due_card(&mut col, &["lsat::lr::flaw"]);
        let unknown = add_due_card(&mut col, &["lsat::lr::not_in_taxonomy"]);
        let t = topics(&[("lsat::lr::weaken", 0.9, 0.0), ("lsat::lr::flaw", 0.5, 0.0)]);

        // limit truncates to the single highest-points card
        let top = col.points_at_stake_queue(DeckId(0), 1, &t).unwrap();
        assert_eq!(top.len(), 1);
        assert_eq!(top[0].top_tag, "lsat::lr::weaken");

        // with no limit, every due card is returned; a card whose tag has no
        // configured weight scores 0 and sorts last.
        let all = col.points_at_stake_queue(DeckId(0), 0, &t).unwrap();
        assert_eq!(all.len(), 3);
        assert_eq!(all.last().unwrap().card_id, unknown);
        assert_eq!(all.last().unwrap().points, 0.0);
        assert_eq!(all.last().unwrap().top_tag, "");
    }

    // ---- QA additions (untested paths) ---------------------------------

    /// Add a due Review card (tags, no FSRS state) into a specific deck.
    fn add_due_card_in_deck(col: &mut Collection, tags: &[&str], deck: DeckId) -> CardId {
        let mut note = NoteAdder::basic(col).fields(&["q", "a"]).note();
        note.tags = tags.iter().map(|t| t.to_string()).collect();
        col.add_note(&mut note, deck).unwrap();
        let card_id = col.storage.card_ids_of_notes(&[note.id]).unwrap()[0];
        let mut card = col.storage.get_card(card_id).unwrap().unwrap();
        card.ctype = CardType::Review;
        card.queue = CardQueue::Review;
        card.due = 0;
        card.memory_state = None;
        col.storage.update_card(&card).unwrap();
        card_id
    }

    /// Add a card with an explicit type/queue (and no FSRS state) in deck 1.
    fn add_card_with_state(
        col: &mut Collection,
        tags: &[&str],
        ctype: CardType,
        queue: CardQueue,
    ) -> CardId {
        let mut note = NoteAdder::basic(col).fields(&["q", "a"]).note();
        note.tags = tags.iter().map(|t| t.to_string()).collect();
        col.add_note(&mut note, DeckId(1)).unwrap();
        let card_id = col.storage.card_ids_of_notes(&[note.id]).unwrap()[0];
        let mut card = col.storage.get_card(card_id).unwrap().unwrap();
        card.ctype = ctype;
        card.queue = queue;
        card.due = 0;
        card.memory_state = None;
        col.storage.update_card(&card).unwrap();
        card_id
    }

    /// Give a card an FSRS memory state and a `secs_ago` last-review time so
    /// that `card_recall` returns a real retrievability in (0, 1).
    fn set_fsrs(col: &mut Collection, cid: CardId, stability: f32, difficulty: f32, secs_ago: i64) {
        let mut card = col.storage.get_card(cid).unwrap().unwrap();
        card.memory_state = Some(FsrsMemoryState {
            stability,
            difficulty,
        });
        card.last_review_time = Some(TimestampSecs::now().adding_secs(-secs_ago));
        col.storage.update_card(&card).unwrap();
    }

    fn recall_of(col: &mut Collection, cid: CardId) -> f32 {
        let timing = col.timing_today().unwrap();
        let card = col.storage.get_card(cid).unwrap().unwrap();
        card_recall(&card, &timing, &FSRS::new(None).unwrap())
    }

    fn entry_for(q: &[PointsAtStakeEntry], cid: CardId) -> &PointsAtStakeEntry {
        q.iter().find(|e| e.card_id == cid).expect("card in queue")
    }

    /// H-A: real FSRS recall (not just the perf term) drives ordering.
    /// Same tag/weight/perf for both cards, same elapsed time; only stability
    /// differs. The low-stability (low-recall => weaker) card must rank first.
    #[test]
    fn hypothesis_a_fsrs_recall_drives_ordering() {
        let mut col = Collection::new();
        let high = add_due_card(&mut col, &["lsat::lr::weaken"]);
        let low = add_due_card(&mut col, &["lsat::lr::weaken"]);
        // identical elapsed (1 day); only stability differs.
        set_fsrs(&mut col, high, 100.0, 5.0, 86_400);
        set_fsrs(&mut col, low, 0.02, 5.0, 86_400);
        let t = topics(&[("lsat::lr::weaken", 0.5, 0.2)]);

        let recall_high = recall_of(&mut col, high);
        let recall_low = recall_of(&mut col, low);

        let q = col.points_at_stake_queue(DeckId(0), 0, &t).unwrap();
        let p_high = entry_for(&q, high).points;
        let p_low = entry_for(&q, low).points;

        println!(
            "[H-A] recall_high={recall_high:.6} recall_low={recall_low:.6} \
             points_high={p_high:.6} points_low={p_low:.6} \
             order=[{},{}] (low={} high={})",
            q[0].card_id.0, q[1].card_id.0, low.0, high.0
        );

        // recall must be a real probability in (0,1) for both, and differ.
        assert!(
            recall_high > 0.0 && recall_high < 1.0,
            "recall_high in (0,1)"
        );
        assert!(recall_low > 0.0 && recall_low < 1.0, "recall_low in (0,1)");
        assert!(
            recall_high > recall_low,
            "higher stability => higher recall"
        );
        // weaker (low-recall) card ranks first.
        assert_eq!(q[0].card_id, low, "low-recall card should rank first");
        assert_eq!(q[1].card_id, high);
        assert!(p_low > p_high, "low-recall card should have more points");
    }

    /// H-B: deck filtering includes the deck + its children, excludes others;
    /// deck_id 0 returns the whole collection.
    #[test]
    fn hypothesis_b_deck_filtering() {
        let mut col = Collection::new();
        let deck_a = DeckAdder::new("A").add(&mut col);
        let deck_a_child = DeckAdder::new("A::child").add(&mut col);
        let deck_b = DeckAdder::new("B").add(&mut col);

        let ca = add_due_card_in_deck(&mut col, &["lsat::lr::weaken"], deck_a.id);
        let cc = add_due_card_in_deck(&mut col, &["lsat::lr::weaken"], deck_a_child.id);
        let cb = add_due_card_in_deck(&mut col, &["lsat::lr::weaken"], deck_b.id);
        let t = topics(&[("lsat::lr::weaken", 0.5, 0.0)]);

        let scoped = col.points_at_stake_queue(deck_a.id, 0, &t).unwrap();
        let scoped_ids: Vec<CardId> = scoped.iter().map(|e| e.card_id).collect();
        println!(
            "[H-B] deck_a={} scoped_ids={:?} (A={} child={} B={})",
            deck_a.id.0, scoped_ids, ca.0, cc.0, cb.0
        );

        assert_eq!(scoped.len(), 2, "only A + A::child");
        assert!(scoped_ids.contains(&ca), "A card present");
        assert!(scoped_ids.contains(&cc), "A::child card present");
        assert!(!scoped_ids.contains(&cb), "B card excluded");

        let all = col.points_at_stake_queue(DeckId(0), 0, &t).unwrap();
        println!("[H-B] whole_collection_len={}", all.len());
        assert_eq!(all.len(), 3, "deck_id 0 returns all decks");
    }

    /// H-C: with multiple weighted tags, `top_tag`/`points` come from the tag
    /// with the highest points, which is *not* always the highest weight.
    #[test]
    fn hypothesis_c_multi_tag_max() {
        // Case 1 (matches the brief): weights 0.3 and 0.9, the 0.9 tag wins.
        let mut col = Collection::new();
        add_due_card(&mut col, &["lsat::rc::main_point", "lsat::lr::weaken"]);
        let t = topics(&[
            ("lsat::rc::main_point", 0.3, 0.0),
            ("lsat::lr::weaken", 0.9, 0.4),
        ]);
        let q = col.points_at_stake_queue(DeckId(0), 0, &t).unwrap();
        // recall 0 (no FSRS) => mastery = 0.5*perf; weaken: 0.9*(1-0.2)=0.72.
        let expected = 0.9 * (1.0 - 0.5 * 0.4);
        println!(
            "[H-C/case1] top_tag={:?} points={:.6} expected={:.6}",
            q[0].top_tag, q[0].points, expected
        );
        assert_eq!(q[0].top_tag, "lsat::lr::weaken");
        assert!((q[0].points - expected).abs() < 1e-6);

        // Case 2: lower-weight tag has higher points => it must win, proving
        // the max is over points and not over weight.
        let mut col2 = Collection::new();
        let _c2 = add_due_card(&mut col2, &["topic_a", "topic_b"]);
        let t2 = topics(&[("topic_a", 0.5, 0.0), ("topic_b", 0.6, 0.9)]);
        let q2 = col2.points_at_stake_queue(DeckId(0), 0, &t2).unwrap();
        let exp_a = 0.5 * (1.0 - 0.5 * 0.0); // 0.50
        let exp_b = 0.6 * (1.0 - 0.5 * 0.9); // 0.33
        println!(
            "[H-C/case2] top_tag={:?} points={:.6} (a={:.4} b={:.4})",
            q2[0].top_tag, q2[0].points, exp_a, exp_b
        );
        assert_eq!(
            q2[0].top_tag, "topic_a",
            "lower-weight, higher-points tag wins"
        );
        assert!((q2[0].points - exp_a).abs() < 1e-6);
    }

    /// H-D: is:due excludes brand-new and suspended cards.
    #[test]
    fn hypothesis_d_state_filtering() {
        let mut col = Collection::new();
        let due = add_due_card(&mut col, &["lsat::lr::weaken"]);
        let new_card = add_card_with_state(
            &mut col,
            &["lsat::lr::weaken"],
            CardType::New,
            CardQueue::New,
        );
        let suspended = add_card_with_state(
            &mut col,
            &["lsat::lr::weaken"],
            CardType::Review,
            CardQueue::Suspended,
        );
        let t = topics(&[("lsat::lr::weaken", 0.9, 0.0)]);

        let q = col.points_at_stake_queue(DeckId(0), 0, &t).unwrap();
        let ids: Vec<CardId> = q.iter().map(|e| e.card_id).collect();
        println!(
            "[H-D] result_ids={:?} (due={} new={} suspended={})",
            ids, due.0, new_card.0, suspended.0
        );

        assert_eq!(q.len(), 1, "only the due card");
        assert!(ids.contains(&due));
        assert!(!ids.contains(&new_card), "new card excluded");
        assert!(!ids.contains(&suspended), "suspended card excluded");
    }

    /// Edge cases: empty collection, deck with no due cards, oversized limit,
    /// and an empty topics list (everything scores 0).
    #[test]
    fn edge_cases() {
        let mut col = Collection::new();
        let t = topics(&[("lsat::lr::weaken", 0.9, 0.0)]);

        // 1) Empty collection => empty result.
        let empty = col.points_at_stake_queue(DeckId(0), 0, &t).unwrap();
        println!("[Edge] empty_collection_len={}", empty.len());
        assert!(empty.is_empty());

        // 2) A deck with no due cards => empty (while another deck has one).
        let empty_deck = DeckAdder::new("Empty").add(&mut col);
        add_due_card(&mut col, &["lsat::lr::weaken"]);
        let none = col.points_at_stake_queue(empty_deck.id, 0, &t).unwrap();
        println!("[Edge] empty_deck_len={}", none.len());
        assert!(none.is_empty());

        // 3) Limit larger than the result count returns everything (2 cards).
        add_due_card(&mut col, &["lsat::lr::weaken"]);
        let big_limit = col.points_at_stake_queue(DeckId(0), 100, &t).unwrap();
        println!("[Edge] big_limit_len={}", big_limit.len());
        assert_eq!(big_limit.len(), 2);

        // 4) Empty topics => every due card scores 0 with empty top_tag.
        let no_topics = col.points_at_stake_queue(DeckId(0), 0, &[]).unwrap();
        println!(
            "[Edge] no_topics_len={} points0={} tag0={:?}",
            no_topics.len(),
            no_topics[0].points,
            no_topics[0].top_tag
        );
        assert_eq!(no_topics.len(), 2);
        for e in &no_topics {
            assert_eq!(e.points, 0.0);
            assert_eq!(e.top_tag, "");
        }
    }
}
