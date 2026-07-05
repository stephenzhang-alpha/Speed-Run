---
name: anki-protobuf-backend
description: "Use this skill whenever adding or modifying a backend method in the Anki fork: defining a new protobuf RPC or message, implementing backend logic in Rust (rslib), and calling it from Python (pylib). Triggers include: the required Rust engine change (e.g. points-at-stake queue, topic-aware scheduling, mastery query), adding a `rpc` to a service, editing a `proto/anki/*.proto` file, getting `col._backend.<method>()` to work from Python, writing the 3 Rust unit tests + 1 Python-calling test, or wiring backend data into the dashboard. Read this BEFORE editing protos or rslib services. Pairs with the anki-build skill (you must rebuild to regenerate protobuf code)."
---

# Adding a protobuf message + Rust backend method, callable from Python

## How the layers fit (confirmed from the repo)

- **Protobuf** (`proto/anki/<area>.proto`) defines both backend methods (as gRPC-style `service`s) and the storage format of some collection items. Definitions are the type-safe contract shared across Rust, Python, and TypeScript. Protobuf is **not** considered public API.
- **rslib** (`rslib/`) is the Rust backend where the real logic lives. Generated proto types are exposed as `anki_proto::<area>::...`; each `service` becomes a Rust **trait** implemented on `Collection` (and sometimes `Backend`).
- **pylib** (`pylib/anki/`) proxies calls to rslib. A private module **rsbridge** (`pylib/rsbridge/`) wraps the Rust code. The collection holds `self._backend` (a `RustBackend`), so backend methods are reachable as `col._backend.<method>()`.
- **GUI** (`qt/aqt/`, `ts/`) consumes pylib and, where useful, the generated TS protobuf types.

Codegen tooling: **prost** (Rust), **protobuf-es** (TS), official protobuf impl (Python). `protoc` is downloaded by the build.

## The 4-step pattern

### 1. Define the message(s) and RPC in a proto

Edit the relevant `proto/anki/<area>.proto`. Services live there already — for scheduling work, that's `proto/anki/scheduler.proto`, which has two services:

- `SchedulerService` — methods available to the collection/front end.
- `BackendSchedulerService` — backend-only methods (it "implicitly includes any of the above methods not listed in the backend service").

Add request/response messages and an `rpc`. Example for a points-at-stake queue:

```protobuf
// in proto/anki/scheduler.proto, inside service SchedulerService { ... }
rpc GetPointsAtStakeQueue(GetPointsAtStakeQueueRequest)
    returns (GetPointsAtStakeQueueResponse);

message GetPointsAtStakeQueueRequest {
  int64 deck_id = 1;
  uint32 limit = 2;
}

message GetPointsAtStakeQueueResponse {
  repeated QueuedCardEntry entries = 1;   // keep repeated field numbers <= 15
}

message QueuedCardEntry {
  int64 card_id = 1;
  float points_at_stake = 2;   // topic_weight * weakness
}
```

Protobuf gotchas to respect (these bite in Anki specifically):

- **Naming:** proto `foo_bar` → `fooBar` in TS, and lives under a `foo_bar` namespace in Rust; an `rpc GetX` becomes `get_x` in Python/Rust.
- **Defaults, not null:** in Python/TS an unset `optional` field returns the type's default (`0`, `""`), not `None`/`undefined`. Use `HasField("name")` / `WhichOneof("bar")` in Python when you must distinguish "unset". In TS, prefer designs that avoid ambiguous defaults (e.g. 1-based indices).
- **Field numbers > 15** need an extra encoding byte, so give `repeated` fields numbers 1–15; `reserved` fields usually exist to leave room for future `repeated` ones.
- **Storage messages** (e.g. `Deck`) are persisted; changing them incompatibly is only safe as part of a schema upgrade. A brand-new request/response message used only for an RPC is fine.

### 2. Rebuild to regenerate code

Run the build so prost/protobuf-es/python regenerate the types (see the `anki-build` skill):

```bash
./run            # or ./ninja
```

To explore the generated Rust types and their impls, from `rslib`:

```bash
cargo doc --open --document-private-items   # look in the `pb` module
```

### 3. Implement the method in Rust (rslib)

After regeneration, the service trait gains your method and **Rust won't compile until you implement it**. Service impls live in `rslib/src/<area>/service/mod.rs`. For the scheduler, the pattern is:

```rust
// rslib/src/scheduler/service/mod.rs
impl crate::services::SchedulerService for Collection {
    fn get_points_at_stake_queue(
        &mut self,
        input: anki_proto::scheduler::GetPointsAtStakeQueueRequest,
    ) -> Result<anki_proto::scheduler::GetPointsAtStakeQueueResponse> {
        // ... query due cards, compute topic_weight * weakness, sort ...
        Ok(anki_proto::scheduler::GetPointsAtStakeQueueResponse { entries })
    }
}
```

Rust-side gotchas:

- An enum field `Foo foo = 1;` is an `i32` on the message; use the accessor `message.foo()` to get the typed `Foo` instead of converting by hand.
- Protobuf doesn't guarantee a oneof is set or an enum is valid, so you'll handle `Option`s. Since other parts of Anki won't send invalid messages, an `InvalidInput` error or `unwrap_or_default()` is usually acceptable.
- **Read vs write:** a pure query (queue ordering, mastery counts) needs no undo entry. A **mutating** method (e.g. reordering cards, changing intervals) must run inside the collection's transaction/op framework and return `OpChanges`/`OpChangesWithCount` so **undo keeps working** and the collection can't be left half-modified. This is the crux of the brief's "prove undo still works and the collection does not corrupt."

### 4. Call it from Python (pylib)

The generated method is on the backend, snake_cased:

```python
out = col._backend.get_points_at_stake_queue(deck_id=did, limit=50)
for entry in out.entries:
    ...
```

Because protobuf isn't public API, expose a clean wrapper in `pylib/anki/scheduler/` (e.g. `v3.py`) rather than having callers touch the generated message — and if you return a protobuf object, alias its type so callers don't import a generated `_pb2` module. (Note: some methods take raw bytes, e.g. `self._backend.import_csv_raw(request.SerializeToString())`; that's only for the bytes-style variants.)

## Tests (the brief requires ≥3 Rust unit tests + 1 Python-calling test)

- **Rust unit tests** in `rslib` (in the area module, `#[cfg(test)] mod test`), opening a test `Collection`, exercising the method on representative data, and — for mutating methods — asserting that an **undo** reverts the change and that reopening the collection yields the same state (no corruption).
- **Python test** under `pylib/tests/` (pytest) that opens a collection and calls `col._backend.<method>()`, asserting the response matches expectations. This is the "calls it from Python" requirement.

## Also required by the brief (challenge 7a)

- A **one-page note: why this belongs in Rust, not Python.** Talking points that are true here: it runs in the scheduler's hot path over 50k cards (needs to be fast and not block the UI); mutations must be transactional/undoable, which the Rust op framework provides; and because the Rust backend is **shared with the AnkiDroid phone build**, implementing it once in Rust ships it to both platforms with identical behaviour and type-safety across languages. A JavaScript/Python reimplementation would diverge and be slow.
- A **list of upstream files you touched** and a **merge-difficulty assessment** — typically `proto/anki/<area>.proto`, `rslib/src/<area>/service/mod.rs`, the relevant `rslib/src/<area>/` logic module, and a `pylib/anki/<area>/` wrapper + a test file. Adding new messages/RPCs and new files merges cleanly; editing existing service method bodies or shared logic is where future rebases onto upstream Anki get harder, so keep changes additive and localized.

## Quick pitfall checklist

- Python doesn't see the new method → you didn't rebuild after editing the proto.
- Rust won't compile after adding an rpc → implement the trait method (that's expected).
- Method should be backend-only → put it in `BackendSchedulerService`, not `SchedulerService`.
- Mutating method breaks undo → wrap it in the transaction/op framework and return `OpChanges`.
- Field reads as `0`/`""` unexpectedly → that's the protobuf default; use `HasField`/`WhichOneof`.
