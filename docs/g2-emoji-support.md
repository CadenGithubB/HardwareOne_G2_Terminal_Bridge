# G2 emoji support

The published G2 `evenemoji` font metrics list **100 pictographic code points**
plus ordinary space and nonbreaking space. This is an explicit inventory,
not support for every emoji in a Unicode block.

## Evidence and limits

Inventory inspected on 2026-10-15 from the public
[@evenrealities/pretext 0.1.4 package](https://www.npmjs.com/package/@evenrealities/pretext/v/0.1.4),
`dist/font_measure.js`, `fontData.fonts[name="evenemoji"].glyphs`.
The package changelog records the addition of the emoji font in 0.1.4.
The [versioned package archive](https://registry.npmjs.org/@evenrealities/pretext/-/pretext-0.1.4.tgz)
has SHA-256 `fe43531945043a923ad21e3309cf3ac79a8d6a46246fa57bf8036ca7402d7abe`.
No package installation, font artwork, or new runtime dependency is needed.

Even's [font measurement documentation](https://github.com/even-realities/everything-evenhub/blob/main/plugins/everything-evenhub/skills/font-measurement/SKILL.md)
warns that missing-glyph behavior may differ between its library and firmware.
Its [simulator release notes](https://www.npmjs.com/package/@evenrealities/evenhub-simulator)
record missing-glyph placeholders and improvements to emoji rendering.
Older simulator-based claims that G2 supports no emoji are not a current inventory.

This list is evidence of published font coverage, not a claim that every glyph
has been visually tested on the native HardwareOne Terminal or every firmware.
The repository's layout profile is for G2 2.3.2.14; the package does not pin this
emoji inventory to that firmware. Confirm the useful palette on the actual
Terminal before treating it as hardware-verified. Glyphs appear on the glasses'
monochrome display; color distinctions should also have text labels.

## Agent guidance

The conversation skill recommends a small subset:

✨ 👍 👀 👌 👏 💪 💯 🔥 😊 🙂 🤔 🎉

Use these as single code points. Prefer words for other status labels.
Use "Done" and "Hello" for status and greetings. Although ✅ and 👋 are listed
in the package, the Terminal policy excludes them because published metrics
do not establish native rendering support. ✓ and ✔ are absent from the package's font
chain. Common agent emoji absent from that chain include 🚀 🛠 📌 ⚠ ❌ 🔧 📅 🔍 💡 🤖.

The skill lives in `skills/terminal-conversation/SKILL.md`. Follow
[the installation instructions](conversation-skill.md) to merge it into the
agent's configured workspace and update its routing guidance. A source edit
here does not install the skill or establish that a live model follows it.

## Terminal display policy

`terminal/device-api.mjs` formats the device presentation before byte limits
and chunking:

- Preserve the published candidates below except ✅ and 👋, which become
  `[check]` and `[wave]`. The remaining inventory is not a firmware certification.
  Also preserve existing pictographs covered by the ordinary
  text fonts: © ® ™ ↔ ↕ ↖ ↗ ↘ ↙ ▶ ◀ ☎ ♀ ♂ ♠ ♣ ♥ ♨.
- Strip U+FE0E/U+FE0F selectors from a recognized single glyph. For example,
  the common two-code-point heart becomes the supported U+2764 heart.
- Replace common unsupported emoji with ASCII labels: ⚠ becomes `[warning]`,
  🛠 becomes `[tools]`, 🚀 becomes `[rocket]`, and 🔍 becomes `[search]`.
- Identify unknown emoji or unsupported composite sequences with their code
  points, such as `[emoji U+1FAE0]`. Skin tones, country flags, keycaps and
  ZWJ combinations are not assumed supported just because one constituent is.
  Their full sequence is retained in the label instead of changing its meaning.
- Preserve unrelated text, including non-Latin writing and combining accents.
  This is an emoji policy, not a complete Unicode font-coverage filter.

Formatting covers assistant replies, displayed user text, tool summaries,
accepted answers, session titles, and question cards. Live text is accumulated
in its original form and reformatted on each update, so a modifier or joiner
arriving in a later delta cannot leave a permanently broken sequence.
OpenClaw transcript contents, prompts, question identifiers, and submitted
answer values remain unchanged. An option's displayed label is separate from
its original value.

Expanded text still obeys the 512-byte item, 64-byte title, 128-byte option,
1024-byte question and 4096-byte response limits. Oversized content and cards
use the existing host-required path. Options that become indistinguishable
also require the host. Permission prompts requiring any substitution are
routed to the host instead of displaying altered approval facts. The original
command or path must be reviewed there.

## Verification

Offline tests exercise allowed and replaced glyphs, selectors, composite
sequences split across stream updates, byte limits after expansion, retained
source text and answer values, ambiguous options, and approval routing.
A separate hardware check should display the small recommended palette,
then compare `✅`, `👋`, `✓`, `⚠️`, `🛠️`, and a joined emoji. Confirm the palette
renders and unsupported inputs show labels rather than the missing-glyph box.
Record firmware and observations privately, outside this public repository.

## Full published emoji inventory

Characters below are bare code points with no appended presentation selectors.
Unicode names identify the code points, not their color on the glasses.
This is a package inventory, not the runtime allowlist: ✅ and 👋 are excluded.

| Glyph | Code point | Unicode name |
| --- | --- | --- |
| ☺ | U+263A | WHITE SMILING FACE |
| ♥ | U+2665 | BLACK HEART SUIT |
| ✅ | U+2705 | WHITE HEAVY CHECK MARK |
| ✨ | U+2728 | SPARKLES |
| ❤ | U+2764 | HEAVY BLACK HEART |
| 🌞 | U+1F31E | SUN WITH FACE |
| 🌸 | U+1F338 | CHERRY BLOSSOM |
| 🌹 | U+1F339 | ROSE |
| 🎁 | U+1F381 | WRAPPED PRESENT |
| 🎂 | U+1F382 | BIRTHDAY CAKE |
| 🎈 | U+1F388 | BALLOON |
| 🎉 | U+1F389 | PARTY POPPER |
| 🎊 | U+1F38A | CONFETTI BALL |
| 🎶 | U+1F3B6 | MULTIPLE MUSICAL NOTES |
| 👀 | U+1F440 | EYES |
| 👇 | U+1F447 | WHITE DOWN POINTING BACKHAND INDEX |
| 👈 | U+1F448 | WHITE LEFT POINTING BACKHAND INDEX |
| 👉 | U+1F449 | WHITE RIGHT POINTING BACKHAND INDEX |
| 👋 | U+1F44B | WAVING HAND SIGN |
| 👌 | U+1F44C | OK HAND SIGN |
| 👍 | U+1F44D | THUMBS UP SIGN |
| 👏 | U+1F44F | CLAPPING HANDS SIGN |
| 👑 | U+1F451 | CROWN |
| 💀 | U+1F480 | SKULL |
| 💋 | U+1F48B | KISS MARK |
| 💐 | U+1F490 | BOUQUET |
| 💓 | U+1F493 | BEATING HEART |
| 💔 | U+1F494 | BROKEN HEART |
| 💕 | U+1F495 | TWO HEARTS |
| 💖 | U+1F496 | SPARKLING HEART |
| 💗 | U+1F497 | GROWING HEART |
| 💙 | U+1F499 | BLUE HEART |
| 💚 | U+1F49A | GREEN HEART |
| 💛 | U+1F49B | YELLOW HEART |
| 💜 | U+1F49C | PURPLE HEART |
| 💞 | U+1F49E | REVOLVING HEARTS |
| 💥 | U+1F4A5 | COLLISION SYMBOL |
| 💩 | U+1F4A9 | PILE OF POO |
| 💪 | U+1F4AA | FLEXED BICEPS |
| 💯 | U+1F4AF | HUNDRED POINTS SYMBOL |
| 💰 | U+1F4B0 | MONEY BAG |
| 🔥 | U+1F525 | FIRE |
| 🖤 | U+1F5A4 | BLACK HEART |
| 😀 | U+1F600 | GRINNING FACE |
| 😁 | U+1F601 | GRINNING FACE WITH SMILING EYES |
| 😂 | U+1F602 | FACE WITH TEARS OF JOY |
| 😃 | U+1F603 | SMILING FACE WITH OPEN MOUTH |
| 😄 | U+1F604 | SMILING FACE WITH OPEN MOUTH AND SMILING EYES |
| 😅 | U+1F605 | SMILING FACE WITH OPEN MOUTH AND COLD SWEAT |
| 😆 | U+1F606 | SMILING FACE WITH OPEN MOUTH AND TIGHTLY-CLOSED EYES |
| 😇 | U+1F607 | SMILING FACE WITH HALO |
| 😈 | U+1F608 | SMILING FACE WITH HORNS |
| 😉 | U+1F609 | WINKING FACE |
| 😊 | U+1F60A | SMILING FACE WITH SMILING EYES |
| 😋 | U+1F60B | FACE SAVOURING DELICIOUS FOOD |
| 😌 | U+1F60C | RELIEVED FACE |
| 😍 | U+1F60D | SMILING FACE WITH HEART-SHAPED EYES |
| 😎 | U+1F60E | SMILING FACE WITH SUNGLASSES |
| 😏 | U+1F60F | SMIRKING FACE |
| 😐 | U+1F610 | NEUTRAL FACE |
| 😑 | U+1F611 | EXPRESSIONLESS FACE |
| 😒 | U+1F612 | UNAMUSED FACE |
| 😔 | U+1F614 | PENSIVE FACE |
| 😘 | U+1F618 | FACE THROWING A KISS |
| 😚 | U+1F61A | KISSING FACE WITH CLOSED EYES |
| 😜 | U+1F61C | FACE WITH STUCK-OUT TONGUE AND WINKING EYE |
| 😞 | U+1F61E | DISAPPOINTED FACE |
| 😡 | U+1F621 | POUTING FACE |
| 😢 | U+1F622 | CRYING FACE |
| 😩 | U+1F629 | WEARY FACE |
| 😬 | U+1F62C | GRIMACING FACE |
| 😭 | U+1F62D | LOUDLY CRYING FACE |
| 😱 | U+1F631 | FACE SCREAMING IN FEAR |
| 😳 | U+1F633 | FLUSHED FACE |
| 😴 | U+1F634 | SLEEPING FACE |
| 🙁 | U+1F641 | SLIGHTLY FROWNING FACE |
| 🙂 | U+1F642 | SLIGHTLY SMILING FACE |
| 🙃 | U+1F643 | UPSIDE-DOWN FACE |
| 🙄 | U+1F644 | FACE WITH ROLLING EYES |
| 🙈 | U+1F648 | SEE-NO-EVIL MONKEY |
| 🙋 | U+1F64B | HAPPY PERSON RAISING ONE HAND |
| 🙌 | U+1F64C | PERSON RAISING BOTH HANDS IN CELEBRATION |
| 🙏 | U+1F64F | PERSON WITH FOLDED HANDS |
| 🤍 | U+1F90D | WHITE HEART |
| 🤎 | U+1F90E | BROWN HEART |
| 🤔 | U+1F914 | THINKING FACE |
| 🤗 | U+1F917 | HUGGING FACE |
| 🤞 | U+1F91E | HAND WITH INDEX AND MIDDLE FINGERS CROSSED |
| 🤣 | U+1F923 | ROLLING ON THE FLOOR LAUGHING |
| 🤤 | U+1F924 | DROOLING FACE |
| 🤦 | U+1F926 | FACE PALM |
| 🤩 | U+1F929 | GRINNING FACE WITH STAR EYES |
| 🤪 | U+1F92A | GRINNING FACE WITH ONE LARGE AND ONE SMALL EYE |
| 🤭 | U+1F92D | SMILING FACE WITH SMILING EYES AND HAND COVERING MOUTH |
| 🤷 | U+1F937 | SHRUG |
| 🥰 | U+1F970 | SMILING FACE WITH SMILING EYES AND THREE HEARTS |
| 🥳 | U+1F973 | FACE WITH PARTY HORN AND PARTY HAT |
| 🥴 | U+1F974 | FACE WITH UNEVEN EYES AND WAVY MOUTH |
| 🥵 | U+1F975 | OVERHEATED FACE |
| 🥺 | U+1F97A | FACE WITH PLEADING EYES |
