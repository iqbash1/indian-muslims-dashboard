# muslimdata.in — navigation tour script

Narration for the self-hosted tour video (`docs/assets/tour.mp4`), embedded on the
About page at `/about/#tour` and reached from the homepage "Watch a short tour" CTA
(Commit GP).

**Voice:** ElevenLabs "Navya Kannan - Conversational" (neutral Indian accent,
professional, clear). Settings used: model `eleven_multilingual_v2`,
stability 0.55, similarity 0.75, style 0.08, speaker boost on. The voice does
NOT read every Indian term natively - "Hindu", "Lok Sabha" and "paise" needed
phonetic respelling (see Pronunciation below); lakh / crore / pucca / Sachar
read fine.
(Note: the library voice literally named "Aisha" is a "virtual girlfriend"
persona, unsuitable for this material; rejected in favour of Navya.)

**Length:** ~550 words, ~3 minutes 34 seconds at a measured pace.

**Shape:** welcome -> orientation -> three movements (who they are -> how they
live -> whether they're heard) -> close. Every figure traces to the canonical CSVs.

**Pronunciation (TTS respellings).** The actual ElevenLabs input is
`vo4-text.txt` in the build dir; it respells terms the model mishears. The
human-readable figures in the script below are voiced via:
- "As-salamu alaykum" (try `Assalamu alaikum` if it clips); "muslimdata dot in"
  reads the URL cleanly.
- **4-digit comma rupees spelled out as words** - "4,455" -> "four thousand four
  hundred and fifty-five", "4,970" -> "four thousand nine hundred and seventy".
  The model otherwise reads "4,455" as "4,155" (the hundreds digit collapses).
- "paise" -> `pie-say`; "Hindu" / "Hindus" -> `Hindhoo` / `Hindhoos` (softer
  dental d, user's call); "Lok Sabha" -> `Lohk sabhaa` (Lok on the "joke"
  vowel, Sabha as "sa-bhaa" - `Loke suh-bha` wrongly voiced "soo-bha");
  closing "Jai Hind" -> `Jaai Hind` (rhymes with "guy" - plain `Jai`/`Jye`
  came out as "jay"/"jye").

---

## Script

**[Welcome]**

As-salamu alaykum, and welcome to muslimdata dot in: a clear, source-traceable picture of how India's Muslims are living, always set beside Hindu and all-India figures. Every number is drawn from a primary source, the Census, the national health and labour surveys, government records, and archived from its original file, so nothing here is invented or second-hand.

**[Orientation]**

The dashboard is a grid of cards across five sections: population, health, education, representation, and justice. On each card, the large number is the Muslim figure, and the pills beside it compare against Hindus and the national average. Click any card, and tabs open the detail beneath. Let me show you three.

**[Movement 1: who they are]**

Start with the simplest question: who are we talking about. India's Muslims are 14.2% of the population, about 20 crore people, the country's largest religious minority. Open the card, and a single number becomes six. "By state" shows where they live, very uneven, from over two-thirds of the people in Jammu and Kashmir down to low single digits elsewhere. "By district" shows how concentrated they are: the hundred most Muslim districts, a sixth of all districts, are home to nearly 59% of all Indian Muslims. "By age" reveals a younger population, and "Decadal growth" shows it grew faster than the country between censuses, from higher fertility that is now falling. One card, six lenses.

**[Movement 2: how they live]**

Next, how people actually live: monthly spending per person, the standard measure of living standards. For Muslims it is about 4,455 rupees, against roughly 4,970 for Hindus, about ninety paise to the rupee. And at the Sachar Committee benchmark in 2004, the ratio was the same, twenty years, and barely a shift. The tab that stands out here is "Top spending fifth." If spending were evenly shared, a fifth of every community would sit in the nation's richest twenty percent. Only 13.7% of Muslims do, the lowest of any community, and even in the cities the gap holds. It is a second measure folded in, so you read how much, and how unequally, in the same place.

**[Movement 3: whether they're heard]**

And one card asks a different question entirely: are they heard. Here it is counted not in percentages, but in seats. Muslims hold 24 of the 543 seats in the Lok Sabha, India's parliament. At their share of the population, fair representation would be 77. And this is the sharpest line on the whole dashboard: Muslim representation peaked at 49 seats in 1980, and has fallen by almost half since, even as their share of the population rose. A gap that widens as numbers grow is not about poverty. It is about voice.

**[Close]**

Every view you have seen can be shared with its own link, or downloaded as a spreadsheet. This is a long-term project: new indicators are added as the data allows, and every figure traces back to the source it came from. Take your time, and explore the numbers for yourself, at muslimdata dot in. Jai Hind.

---

## Figure provenance (for re-checks)

| Movement | Claim | Source |
|---|---|---|
| pop-share | 14.2% / ~20 crore; largest minority | `canonical/pop-share.csv` (Census 2011) |
| pop-share | top-100 districts hold 58.6% | `canonical/district-concentration-top100.csv` |
| pop-share | grew 24.6% vs 17.7% all-India (2001-2011) | `canonical/pop-growth-decadal.csv` |
| mpce | Muslim 4,455 vs Hindu 4,974 (2023); 2004 Sachar 635 vs 712 | `canonical/mpce.csv` |
| mpce | only 13.7% in the top spending fifth | `canonical/top-quintile-share.csv` |
| ls-share | 24 of 543; parity 77; peaked 49 in 1980 | `canonical/ls-share.csv` |
