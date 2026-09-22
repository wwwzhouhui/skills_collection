# Page pattern

## Recommended architecture

- one independent HTML entry per poem;
- one TypeScript page module and one CSS file;
- a small poem configuration containing metadata, image paths, and section copy;
- fixed background image stage;
- normal document-flow sections above it;
- chapter navigation and cross-links to other poems.

## Image stage

Use either:

1. two Three.js `PlaneGeometry` layers with `MeshBasicMaterial`, or
2. two fixed `<img>` elements.

On active-section change:

1. load/set the next image on the front layer;
2. fade front opacity from 0 to 1;
3. copy the next image to the back layer;
4. reset front opacity to 0.

Fit 16:9 imagery by aspect ratio. On narrow screens, fit by width and use a blurred `cover` backdrop behind it.

## Active section selection

Choose the section whose top is closest to about 28–32% of the viewport. Do not switch purely by total scroll percentage when sections have different heights.

## Narration

- Include one narration track per poem page, preferably supplied by the user or already present in the project.
- Attempt audible autoplay, but expect `NotAllowedError` in normal browsers.
- Always render a visible play/pause button with a text label, `aria-pressed`, and keyboard focus styling.
- Treat blocked autoplay as an idle state, not an error. A user click must start playback.
- Show an inline/local “audio unavailable” state for network or decoding failures.
- Verify the final public URL returns a successful audio response before delivery.
- Do not loop the poem unless the user explicitly asks.

## Copy cards

- width: 42–48vw desktop, nearly full width mobile;
- translucent dark or light material derived from the image palette;
- line-height around 1.8–2 for Chinese explanation;
- primary line at 34–64px desktop;
- one visual micro-component per card, not a dashboard of widgets.

## Performance

- keep the full-resolution Ark output out of the served manifest, or reference only the
  derivatives from code;
- the API already returns JPEG at roughly 250–500 KB for 2560x1440, which is directly
  servable — downscale only when a variant is genuinely smaller on the wire;
- preload the hero, then allow later images to load normally;
- use no more than subtle pointer parallax;
- reuse a shared Three.js chunk across multi-page Vite entries.

## QA checklist

- loading overlay disappears;
- title and defining line are readable at first paint;
- hero subject is not covered by typography;
- every navigation item maps to one section;
- background visibly changes after the fade settles;
- no image has accidental text, seal, or watermark;
- reduced motion works;
- narration plays after a user click when autoplay is blocked;
- mobile cards do not cover the full focal subject;
- build passes and browser console is clean.
