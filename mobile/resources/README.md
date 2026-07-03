# App icons & splash

`icon.svg` is the source mark. Capacitor's asset generator wants a 1024x1024
PNG, so export the SVG first, then generate the Android densities:

```bash
# from mobile/ (any SVG->PNG tool works; e.g. rsvg-convert / Inkscape / an editor)
rsvg-convert -w 1024 -h 1024 resources/icon.svg -o resources/icon.png
# optional: a splash logo (defaults to the icon if omitted)
cp resources/icon.png resources/splash.png    # or a wider logo on #f4f6f9

npm run assets    # @capacitor/assets -> android mipmaps + splash
```

`@capacitor/assets` writes into the generated `android/` project, so run it
after `npx cap add android`.
