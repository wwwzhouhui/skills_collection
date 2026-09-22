# Image direction

Images are produced through `scripts/ark_image.py` by one of two providers: Volcengine Ark (火山引擎方舟) Doubao Seedream, or a GPT-Image gateway. Which one is used is decided by the tier, so the prompt guidance below applies to both — read [ark-api.md](ark-api.md) for each provider's parameters, size rules and error handling.

## Visual bible

Define before generating:

- medium: historical film still, macro diorama photography, photographic landscape, restrained painterly cinema;
- period and geography;
- recurring characters: age, clothing, silhouette, props, placement;
- palette: 4–6 descriptive colors;
- light progression across beats;
- lens and composition language;
- material list;
- avoid list.

Repeat the stable parts of this bible in every prompt. Consistency is more important than novelty.

## Prompt style for Seedream

Seedream responds best to **one natural-language paragraph**. Do not use Midjourney-style flags such as `--ar 16:9` or `--no text`: the API has no such parameters, so they are billed as ordinary prompt words and risk being rendered as literal text in the picture.

State the frame, the composition, and the exclusions in prose, inside the single `prompt` string:

- frame and layout: “16:9 wide horizontal frame, <focal layout>, quiet negative space on the right for Chinese typography”;
- exclusions: “no text, calligraphy, seals, signatures, watermarks, logos, or modern objects anywhere in the image”. There is no negative-prompt field, so this clause has to be part of the prompt.

Aspect ratio comes from `size` (`2560x1440`), never from prompt text.

## Hero prompt template (text-to-image)

```text
A 16:9 wide horizontal cinematic still for the landing hero of <title>: <the poem's entire emotional world in one composition>. Rendered as <realistic medium and production quality>, <period and geography>, <time of day, weather, emotional temperature>. <Focal layout> with quiet negative space on the right for Chinese typography. Lens and color science: <focal length, depth of field, grade>. Materials: <specific surfaces and textures>. No text, calligraphy, seals, signatures, watermarks, logos, or modern objects anywhere in the image; avoid cartoon, low-poly, plastic-toy, and generic game-art rendering.
```

```bash
python scripts/ark_image.py t2i --role hero --size 2560x1440 \
  --prompt "<hero paragraph>" --out public/generated/<poem-slug>/hero.jpg
```

## Beat prompt template (image-to-image, hero as reference)

```text
Continue the world of the reference image exactly: same geography, period, recurring characters, wardrobe, props, materials, palette, weather progression, and lens language. Now show scene <N> of <title>: <filmable action derived from the original line "<original line>">. Move the camera and the emphasis, not the art direction. 16:9 wide horizontal frame, <focal subject placement>, quiet negative space on <copy side> for Chinese typography. Lighting: <beat-specific progression>. Mood: <beat-specific emotion>. No text, calligraphy, seals, signatures, watermarks, logos, or modern objects anywhere in the image.
```

```bash
python scripts/ark_image.py i2i --role beat --ref public/generated/<poem-slug>/hero.jpg \
  --prompt "<beat paragraph>" --out public/generated/<poem-slug>/scene-1.jpg
```

Keep the stable bible wording identical across prompts so the text and the reference image push in the same direction.

## Reference-image chain (image-to-image)

- Generate the hero first with text-to-image, and treat it as canon.
- Generate every later beat with the hero as a reference — `--ref <hero>` on a single call, or `"ref": ["hero"]` in a batch plan — so geography, wardrobe, props, palette, and lens language stay identical instead of being re-described from scratch.
- When a beat introduces a new recurring character, generate that character deliberately first, then register the image as a reference for every later beat in which the character appears.
- The API accepts several references in one call, so a beat may pass the hero **plus** a character reference: `--ref hero.jpg --ref <character>.jpg`. Say in the prompt which reference owns what, since the array carries no roles.
- In a batch plan, list the hero before any beat that references it; `"ref": ["hero"]` resolves against images already generated inside `out_dir`.
- If one beat still drifts, repair that beat with the hero still attached rather than rebuilding the whole chain. Regenerate the hero only when the world design itself changes.

## Consistency rules

- Generate hero first, then chain every later image to it by reference.
- Recurring figures must keep age, hair, clothing family, silhouette, and props.
- Keep geography navigable: the same river, village, mountain, road, room, or battlefield should remain recognizable.
- Move the camera and emphasis, not the entire art direction.
- Use a logical light progression when the poem changes time.

## Common failures

- “Ancient Chinese style” alone produces generic fantasy.
- Miniature/diorama without “physically realistic macro photography” produces plastic toys.
- War prompts without restraint produce video-game spectacle.
- Asking for calligraphy inside images creates corrupted text; render all text in HTML.
- One prompt generating multiple distinct scenes weakens control; use separate calls.
- An image can look excellent alone yet drift from the set. Always inspect a contact sheet.
- Passing `"2K"`, or any shorthand, instead of an explicit `WIDTHxHEIGHT` silently yields a non-16:9 frame — a landscape prompt came back 1664x2496, portrait.
- `doubao-seedream-5.0-lite` rejects any size below 3,686,400 px, and both tiers reject anything above 4,624,220 px. `2560x1440` (3,686,400 px) is the only 16:9 value both tiers accept.
- Skipping the reference chain reintroduces character and geography drift: a text-only prompt cannot hold a face, a village, or a river mouth steady across eight images.
- On the GPT-Image gateway the ratio you ask for is the ratio you get, but the resolution is normalised to roughly 1670 px on the long edge: ask for a true 16:9 size (`2560x1440` or `1920x1080`) and never `1792x1024` (7:4) or `auto` (4:3) when the frame has to fill a 16:9 page stage.
