# Conceptual Similarity Score Few-Shot Examples

<few_shot_examples>

<example1>
<assessment1>
This example demonstrates the "meaningless marks" baseline: invented words with no semantic content in any EU language receive 0.0 score. Key principle: (1) Conceptual similarity requires actual meaning, not just structural resemblance, (2) Phonetic similarity (ZAR-) doesn't create conceptual connection, (3) EU trademark law distinguishes between form and meaning. This establishes that made-up marks cannot be conceptually similar regardless of visual/aural overlap.
</assessment1>
<input1>
- **Mark 1:** `ZAREUS`
- **Mark 2:** `ZARA`
</input1>
<output_json1>
{
  "score": 0.0
}
</output_json1>
</example1>

<example2>
<assessment2>
This example illustrates the "semantic dilution" principle where adding elements changes conceptual meaning. Critical factors: (1) GABRIELLE alone = common forename (neutral/personal association), (2) GABRIELLE CHANEL = specific fashion brand (luxury/commercial association), (3) The addition transforms the concept from generic to specific. This tests whether shared elements create conceptual similarity when their semantic fields differ significantly.
</assessment2>
<input2>
- **Mark 1:** `GABRIELLE`
- **Mark 2:** `GABRIELLE CHANEL`
</input2>
<output_json2>
{
  "score": 0.2
}
</output_json2>
</example2>

<example3>
<assessment3>
This example reinforces the invented marks principle: phonetically similar nonsense words remain conceptually dissimilar. Key considerations: (1) Neither mark has dictionary meaning in major EU languages, (2) Sound similarity (OLTEN/OLTENE) doesn't create semantic connection, (3) Consumers cannot derive meaning from invented terms. This confirms that conceptual analysis requires actual semantic content, not just pattern matching.
</assessment3>
<input3>
- **Mark 1:** `VOLTEN`
- **Mark 2:** `FOLTENE`
</input3>
<output_json3>
{
  "score": 0.0
}
</output_json3>
</example3>

<example4>
<assessment4>
This example demonstrates "perfect translation equivalence" - the highest conceptual similarity scenario. Critical factors: (1) AQUA (Latin) and WATER (English) have identical semantic meaning, (2) Both widely understood across EU markets, (3) Direct translation relationship creates maximum conceptual overlap. This establishes the 0.95 ceiling for conceptual similarity (not 1.0 due to language difference creating minimal distinction).
</assessment4>
<input4>
- **Mark 1:** `AQUA`
- **Mark 2:** `WATER`
</input4>
<output_json4>
{
  "score": 0.95
}
</output_json4>
</example4>

<example5>
<assessment5>
This example shows "thematic association" without direct semantic overlap. Key principles: (1) KING and ROYAL both relate to monarchy/nobility concepts, (2) Different word classes (noun vs. adjective) create distinction, (3) Shared semantic field but not synonyms. This tests moderate conceptual similarity where marks evoke related ideas without being translations or synonyms.
</assessment5>
<input5>
- **Mark 1:** `KING`
- **Mark 2:** `ROYAL`
</input5>
<output_json5>
{
  "score": 0.6
}
</output_json5>
</example5>

<example6>
<assessment6>
This example illustrates "partial semantic overlap" through compound words. Critical edge case: (1) SUN appears in both marks creating shared element, (2) SUNSHINE suggests brightness/happiness while SUNSET suggests ending/twilight, (3) Different emotional associations despite shared root. This tests whether common word elements create conceptual similarity when the compound meanings diverge.
</assessment6>
<input6>
- **Mark 1:** `SUNSHINE`
- **Mark 2:** `SUNSET`
</input6>
<output_json6>
{
  "score": 0.4
}
</output_json6>
</example6>

<example7>
<assessment7>
This example demonstrates "identical concept expression" where marks use the same words to convey identical meaning. Key factors: (1) Both marks combine "Be" + "Real" in identical fashion, (2) Same grammatical construction (imperative + adjective), (3) Identical message of authenticity/genuineness. This represents perfect conceptual identity (1.0) as the marks convey exactly the same idea using the same linguistic elements.
</assessment7>
<input7>
- **Mark 1:** `BeReal`
- **Mark 2:** `BeReal`
</input7>
<output_json7>
{
  "score": 1.0
}
</output_json7>
</example7>

<example8>
<assessment8>
This example illustrates "technical vs. generic meaning divergence" in technology marks. Critical distinctions: (1) XCODE clearly references "code" suggesting programming/software development, (2) XCORE suggests "core" implying central/fundamental component, (3) Both use "X" prefix common in tech branding but convey different functions. This tests how similar-sounding tech marks can have distinct conceptual meanings based on their root words.
</assessment8>
<input8>
- **Mark 1:** `XCORE`
- **Mark 2:** `XCODE`
</input8>
<output_json8>
{
  "score": 0.0
}
</output_json8>
</example8>

<example9>
<assessment9>
This example shows "descriptive element combination" where one mark adds a highly descriptive term. Key principles: (1) L'OR means "the gold" in French, suggesting premium quality, (2) CAFÉ D'OR means "golden coffee", combining the premium association with product description, (3) The addition of CAFÉ narrows but maintains the luxury/quality concept. This tests moderate conceptual similarity where descriptive additions modify but don't eliminate shared conceptual elements.
</assessment9>
<input9>
- **Mark 1:** `CAFÉ D'OR`
- **Mark 2:** `L'OR`
</input9>
<output_json9>
{
  "score": 0.3
}
</output_json9>
</example9>

<example10>
<assessment10>
This example demonstrates "phonetic identity with conceptual equivalence" through spelling variations. Critical factors: (1) Both derive from "snug" conveying comfort/coziness, (2) Y/IE ending variation doesn't change meaning, (3) Diminutive form maintains the same cozy/comfortable concept. This shows high conceptual similarity (0.9) where minor spelling differences don't affect the underlying semantic content.
</assessment10>
<input10>
- **Mark 1:** `snuggy`
- **Mark 2:** `SNUGGIE`
</input10>
<output_json10>
{
  "score": 0.9
}
</output_json10>
</example10>

<example11>
<assessment11>
This example demonstrates why marks sharing a common field or industry theme are NOT conceptually similar. Critical principle: (1) BIOME suggests biological/ecological systems, (2) BIO suggests organic/biological products, (3) While both relate to "biological" themes, they evoke entirely different concepts - ecosystem vs. organic certification. This shows that industry-related terms don't create conceptual similarity without evoking the same core idea.
</assessment11>
<input11>
- **Mark 1:** `BIOME`
- **Mark 2:** `BIO`
</input11>
<output_json11>
{
  "score": 0.1
}
</output_json11>
</example11>

<example12>
<assessment12>
This example illustrates that personal names combined with descriptive terms don't create conceptual similarity. Key factors: (1) BODICA is a distinctive personal/brand name with no inherent meaning, (2) BODY CARE clearly describes personal care/cosmetic services, (3) The phonetic echo (BOD-) doesn't create conceptual connection when one mark is meaningless. This reinforces that sound similarity ≠ conceptual similarity.
</assessment12>
<input12>
- **Mark 1:** `BODICA`
- **Mark 2:** `BODY CARE`
</input12>
<output_json12>
{
  "score": 0.0
}
</output_json12>
</example12>

<example13>
<assessment13>
This example shows how marks in the same industry can be conceptually dissimilar. Critical distinctions: (1) CM suggests initials/abbreviation with no inherent gaming meaning, (2) GAMES clearly indicates entertainment/gaming products, (3) Even in gaming context, CM doesn't evoke gaming concepts to average consumers. This demonstrates that context doesn't create similarity where none exists conceptually.
</assessment13>
<input13>
- **Mark 1:** `CM GAMES`
- **Mark 2:** `GAMES`
</input13>
<output_json13>
{
  "score": 0.0
}
</output_json13>
</example13>

<example14>
<assessment14>
This example demonstrates acronym vs. full word dissimilarity. Key principles: (1) COPA could be abbreviation/foreign word with no clear English meaning, (2) CUP has specific meaning (drinking vessel/trophy), (3) Even if COPA means "cup" in Spanish, average UK/EU consumers may not make this connection. This shows that foreign language meanings don't necessarily create conceptual similarity for average consumers.
</assessment14>
<input14>
- **Mark 1:** `COPA`
- **Mark 2:** `CUP`
</input14>
<output_json14>
{
  "score": 0.2
}
</output_json14>
</example14>

<example15>
<assessment15>
This example illustrates why descriptive combinations don't equal conceptual similarity. Critical factors: (1) COTTON REPUBLIC suggests a brand focused on cotton products, (2) REPUBLIC alone suggests governance/state concept, (3) Adding "COTTON" completely changes the conceptual focus from political to commercial. This shows how qualifiers transform conceptual meaning even when sharing elements.
</assessment15>
<input15>
- **Mark 1:** `COTTON REPUBLIC`
- **Mark 2:** `REPUBLIC`
</input15>
<output_json15>
{
  "score": 0.1
}
</output_json15>
</example15>

<example16>
<assessment16>
This example shows invented marks cannot be conceptually similar to meaningful words. Key principle: (1) AESKUCARE appears to be invented mark suggesting care services, (2) HEALTHCARE has clear, established meaning, (3) Even with "CARE" element, an invented mark cannot share concepts with established terms. Average consumers cannot derive meaning from invented portions.
</assessment16>
<input16>
- **Mark 1:** `AESKUCARE`
- **Mark 2:** `HEALTHCARE`
</input16>
<output_json16>
{
  "score": 0.0
}
</output_json16>
</example16>

<example17>
<assessment17>
This example demonstrates that mythological/religious references don't create similarity without shared meaning. Critical factors: (1) EYE OF ATUM references Egyptian deity/mythology, (2) EYE alone is body part/vision concept, (3) Mythological context creates entirely different conceptual field. This shows specialized cultural references don't create similarity with common words.
</assessment17>
<input17>
- **Mark 1:** `EYE OF ATUM`
- **Mark 2:** `EYE`
</input17>
<output_json17>
{
  "score": 0.1
}
</output_json17>
</example17>

<example18>
<assessment18>
This example illustrates how technical/gaming terms remain conceptually distinct. Key principles: (1) INVICTUS suggests "unconquered/invincible" (Latin), (2) GAMES indicates entertainment products, (3) Even as "Invictus Games" (sports event), the marks evoke different concepts - strength/victory vs. entertainment. This shows compound marks don't share concepts with their individual elements.
</assessment18>
<input18>
- **Mark 1:** `INVICTUS GAMES`
- **Mark 2:** `GAMES`
</input18>
<output_json18>
{
  "score": 0.1
}
</output_json18>
</example18>

<example19>
<assessment19>
This example shows how luxury brand indicators don't create conceptual similarity. Critical distinctions: (1) LV commonly understood as luxury brand abbreviation (Louis Vuitton), (2) BESPOKE means custom-made/tailored, (3) Both suggest luxury/quality but through entirely different concepts - brand prestige vs. customization. This demonstrates that similar market positioning ≠ conceptual similarity.
</assessment19>
<input19>
- **Mark 1:** `LV BESPOKE`
- **Mark 2:** `LUXURY`
</input19>
<output_json19>
{
  "score": 0.2
}
</output_json19>
</example19>

<example20>
<assessment20>
This example reinforces that phonetic similarity doesn't create conceptual similarity. Key factors: (1) YATTER suggests chatter/talk (informal speech), (2) TWITTER is established social media platform, (3) Despite rhyming structure, marks evoke different concepts - generic talking vs. specific platform. This shows that sound patterns don't establish conceptual connections.
</assessment20>
<input20>
- **Mark 1:** `YATTER`
- **Mark 2:** `TWITTER`
</input20>
<output_json20>
{
  "score": 0.2
}
</output_json20>
</example20>

<example21>
<assessment21>
This negative example explicitly shows why these marks are NOT conceptually similar despite surface connections. Critical reasoning: (1) FLUX suggests flow/change/movement, (2) GEAR suggests equipment/mechanism/clothing, (3) In tech context, still evoke different ideas - data flow vs. equipment/tools, (4) Compound "FLUX GEAR" doesn't bridge conceptual gap. This demonstrates that combining unrelated concepts doesn't create similarity with either component.
</assessment21>
<input21>
- **Mark 1:** `FLUX GEAR`
- **Mark 2:** `FLUX`
</input21>
<output_json21>
{
  "score": 0.0
}
</output_json21>
</example21>

<example22>
<assessment22>
This example shows why location/building references don't equal conceptual similarity. Key principles: (1) ONE PLANET suggests environmental/global unity concept, (2) PLANET alone is astronomical body, (3) Adding "ONE" creates sustainability/environmental message absent from PLANET alone. This illustrates how modifiers can completely transform conceptual meaning.
</assessment22>
<input22>
- **Mark 1:** `ONE PLANET`
- **Mark 2:** `PLANET FITNESS`
</input22>
<output_json22>
{
  "score": 0.1
}
</output_json22>
</example22>

</few_shot_examples> 