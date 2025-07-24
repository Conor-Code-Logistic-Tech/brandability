# Goods/Services Likelihood Assessment Few-Shot Examples

<few_shot_examples>

<example1>
<assessment1>
This example from the Serial Killer case demonstrates that "apparel" and "clothing" are direct synonyms that must receive maximum similarity score. These terms are interchangeable in the fashion industry - "apparel" is simply the American English term for "clothing". Both terms describe the same category of goods: garments worn on the body. The fact they're both in Class 25 reinforces this, but even across different classes, these identical concepts would score 1.0.
</assessment1>
<input1>
- **Applicant Good/Service:** `apparel` (Class 25)
- **Opponent Good/Service:** `Clothing` (Class 25)
- **Mark Similarity Context:**
  - Visual: "moderate"
  - Aural: "low"
  - Conceptual: "moderate"
  - Overall: "moderate"
</input1>
<output_json1>
{
  "are_competitive": true,
  "are_complementary": false,
  "similarity_score": 1.0,
  "likelihood_of_confusion": true,
  "confusion_type": "direct"
}
</output_json1>
</example1>

<example2>
<assessment2>
This example from the Wakeful case shows identical vitamin preparations that must score maximum similarity. "Vitamin supplements" and "Vitamin and mineral preparations" are functionally identical - supplements ARE preparations containing vitamins/minerals. The slight wording variation ("supplements" vs "preparations", inclusion of "mineral") doesn't change that these are the same products. Class 5 pharmaceutical goods require high attention, but identical goods always score 0.9+.
</assessment2>
<input2>
- **Applicant Good/Service:** `Vitamin supplements` (Class 5)
- **Opponent Good/Service:** `Vitamin and mineral preparations` (Class 5)
- **Mark Similarity Context:**
  - Visual: "low"
  - Aural: "moderate"
  - Conceptual: "high"
  - Overall: "moderate"
</input2>
<output_json2>
{
  "are_competitive": true,
  "are_complementary": false,
  "similarity_score": 1.0,
  "likelihood_of_confusion": true,
  "confusion_type": "direct"
}
</output_json2>
</example2>

<example3>
<assessment3>
This example from the AESKUCARE case demonstrates that "Medical instruments" and "Surgical instruments" are near-identical, with surgical being a specific type of medical instrument. In trademark law, when one term encompasses the other, they're treated as identical for opposition purposes. Medical professionals would understand surgical instruments ARE medical instruments, creating complete overlap. The high attention in medical fields doesn't reduce goods similarity.
</assessment3>
<input3>
- **Applicant Good/Service:** `Medical instruments` (Class 10)
- **Opponent Good/Service:** `Surgical instruments` (Class 10)
- **Mark Similarity Context:**
  - Visual: "low"
  - Aural: "moderate"
  - Conceptual: "dissimilar"
  - Overall: "low"
</input3>
<output_json3>
{
  "are_competitive": true,
  "are_complementary": false,
  "similarity_score": 1.0,
  "likelihood_of_confusion": true,
  "confusion_type": "direct"
}
</output_json3>
</example3>

<example4>
<assessment4>
This example demonstrates the "interdependence principle" at its core: identical goods with moderate mark similarity leading to confusion. Critical factors: (1) "Athletic jackets" are a specific subset of "Articles of clothing", creating 100% overlap, (2) Same Nice class (25) and distribution channels, (3) EU law holds that identical goods lower the similarity threshold for marks. This tests whether moderate mark similarity suffices when goods are identical - a fundamental trademark principle.
</assessment4>
<input4>
- **Applicant Good/Service:** `Athletic jackets` (Class 25)
- **Opponent Good/Service:** `Articles of clothing for men, women and children` (Class 25)
- **Mark Similarity Context:**
  - Visual: "moderate"
  - Aural: "low"
  - Conceptual: "dissimilar"
  - Overall: "moderate"
</input4>
<output_json4>
{
  "are_competitive": true,
  "are_complementary": false,
  "similarity_score": 1.0,
  "likelihood_of_confusion": true,
  "confusion_type": "direct"
}
</output_json4>
</example4>

<example5>
<assessment5>
This example illustrates the "medical exception" edge case: when identical-looking products serve fundamentally different purposes. Key distinctions: (1) Class 10 compression garments are medical devices with therapeutic function, (2) Distribution through pharmacies/medical suppliers vs. retail clothing stores, (3) Different consumer attention levels (medical purchases involve higher care). This tests the boundary between Classes 10 and 25, where physical similarity doesn't equal legal similarity.
</assessment5>
<input5>
- **Applicant Good/Service:** `Compression garments, namely, Compression Socks, Compression stocking, Compression leggings, Compression pants, Compression shirts, Compression Jerseys, Compression Vests, Compression Sleeves` (Class 10)
- **Opponent Good/Service:** `Articles of clothing for men, women and children` (Class 25)
- **Mark Similarity Context:**
  - Visual: "moderate"
  - Aural: "low"
  - Conceptual: "dissimilar"
  - Overall: "moderate"
</input5>
<output_json5>
{
  "are_competitive": false,
  "are_complementary": false,
  "similarity_score": 0.3,
  "likelihood_of_confusion": false,
  "confusion_type": null
}
</output_json5>
</example5>

<example6>
<assessment6>
This example shows the clearest application of direct confusion: identical products (shampoos) with high mark similarity. Key principles: (1) Same exact product = similarity score 1.0, (2) High mark similarity + identical goods = automatic confusion under EU law, (3) Personal care products involve low consumer attention (routine purchases). This establishes the baseline for when opposition must succeed - no edge cases or exceptions apply.
</assessment6>
<input6>
- **Applicant Good/Service:** `Shampoos` (Class 3)
- **Opponent Good/Service:** `shampoos` (Class 3)
- **Mark Similarity Context:**
  - Visual: "moderate"
  - Aural: "high"
  - Conceptual: "dissimilar"
  - Overall: "high"
</input6>
<output_json6>
{
  "are_competitive": true,
  "are_complementary": false,
  "similarity_score": 1.0,
  "likelihood_of_confusion": true,
  "confusion_type": "direct"
}
</output_json6>
</example6>

<example7>
<assessment7>
This example demonstrates "indirect confusion" through complementary goods in the personal care sector. Critical factors: (1) Skincare and hair care products often sold side-by-side in same retail locations, (2) Same manufacturers frequently produce both categories under unified branding, (3) Consumers expect brand consistency across personal care lines. This tests the "economic connection" doctrine where non-competing goods create confusion through commercial proximity and consumer expectations.
</assessment7>
<input7>
- **Applicant Good/Service:** `skincare products` (Class 3)
- **Opponent Good/Service:** `Hair care products` (Class 3)
- **Mark Similarity Context:**
  - Visual: "moderate"
  - Aural: "high"
  - Conceptual: "dissimilar"
  - Overall: "high"
</input7>
<output_json7>
{
  "are_competitive": false,
  "are_complementary": true,
  "similarity_score": 0.75,
  "likelihood_of_confusion": true,
  "confusion_type": "indirect"
}
</output_json7>
</example7>

<example8>
<assessment8>
This example illustrates the "software generalization" principle in Class 9 technology goods. Key factors: (1) "Software" is a broad term encompassing all specific software types, (2) Development tools are a subset of general software, (3) Technology sector shows high brand extension expectations. This tests whether broad software claims create confusion with specific software types, crucial for technology oppositions where specifications vary in granularity.
</assessment8>
<input8>
- **Applicant Good/Service:** `Software` (Class 9)
- **Opponent Good/Service:** `Computer software and firmware for operating system programs and application development tool programs` (Class 9)
- **Mark Similarity Context:**
  - Visual: "moderate"
  - Aural: "low"
  - Conceptual: "dissimilar"
  - Overall: "moderate"
</input8>
<output_json8>
{
  "are_competitive": true,
  "are_complementary": false,
  "similarity_score": 1.0,
  "likelihood_of_confusion": true,
  "confusion_type": "direct"
}
</output_json8>
</example8>

<example9>
<assessment9>
This example demonstrates the "hardware vs. software divide" in technology goods. Critical distinctions: (1) Smart bracelets are physical wearable devices, (2) Development tools are intangible software products, (3) Different distribution channels (electronics retail vs. software licensing). This tests the boundary between tangible tech hardware and software services, relevant as IoT devices blur traditional classifications.
</assessment9>
<input9>
- **Applicant Good/Service:** `Smart bracelets` (Class 9)
- **Opponent Good/Service:** `Downloadable computer software development tools` (Class 9)
- **Mark Similarity Context:**
  - Visual: "moderate"
  - Aural: "low"
  - Conceptual: "dissimilar"
  - Overall: "moderate"
</input9>
<output_json9>
{
  "are_competitive": false,
  "are_complementary": false,
  "similarity_score": 0.2,
  "likelihood_of_confusion": false,
  "confusion_type": null
}
</output_json9>
</example9>

<example10>
<assessment10>
This example illustrates "cross-class complementarity" between coffee products (Class 30) and retail services (Class 35). Key factors: (1) Coffee retail services directly involve the underlying coffee products, (2) Consumers expect vertical integration in coffee industry (roasters operating cafes), (3) Services specifically mention the identical goods. This tests whether retail services for specific goods create confusion with the goods themselves - a common issue in modern commerce.
</assessment10>
<input10>
- **Applicant Good/Service:** `wholesaling and retailing, including via the internet, of coffee, coffee pods, coffee capsules` (Class 35)
- **Opponent Good/Service:** `Coffee, also coffee in filter packing, coffee-based beverages` (Class 30)
- **Mark Similarity Context:**
  - Visual: "moderate"
  - Aural: "moderate"
  - Conceptual: "dissimilar"
  - Overall: "moderate"
</input10>
<output_json10>
{
  "are_competitive": false,
  "are_complementary": true,
  "similarity_score": 0.6,
  "likelihood_of_confusion": true,
  "confusion_type": "indirect"
}
</output_json10>
</example10>

<example11>
<assessment11>
This example demonstrates the "wearable blanket paradox" - products that blur traditional categories. Critical factors: (1) Blankets with sleeves combine textile (Class 24) and clothing (Class 25) characteristics, (2) Same end-use (warmth/comfort) but different classification approaches, (3) Marketing often positions these ambiguously. This edge case tests how hybrid products that challenge traditional Nice classifications are assessed for similarity, particularly relevant as product innovation creates category-defying goods.
</assessment11>
<input11>
- **Applicant Good/Service:** `blankets with sleeves` (Class 24)
- **Opponent Good/Service:** `wearable blankets with sleeves` (Class 24)
- **Mark Similarity Context:**
  - Visual: "high"
  - Aural: "high"
  - Conceptual: "high"
  - Overall: "high"
</input11>
<output_json11>
{
  "are_competitive": true,
  "are_complementary": false,
  "similarity_score": 1.0,
  "likelihood_of_confusion": true,
  "confusion_type": "direct"
}
</output_json11>
</example11>

</few_shot_examples> 