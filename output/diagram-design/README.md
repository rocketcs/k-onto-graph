# Semantica diagrams

Four diagrams rebuilt with diagram-design, using project-specific white, blue and teal styling. Each SVG has a 1280 x 720 viewBox; PNG exports use 2x resolution. Text is editable in SVG. Open index.html for the gallery.

Content follows the prior verified code review and source prompts in ../imagegen. The overview aggregates secondary platform components. The extraction example is illustrative, not an actual execution result. No measured accuracy is claimed.

Implementation references:
- semantica/semantic_extract/ner_extractor.py and methods.py: extraction methods and LLM prompts.
- semantica/ontology/engine.py: ontology construction and explicit validation entry points.
- semantica/reasoning/reasoner.py: facts, rules and chaining.
- semantica/provenance/manager.py: source and lineage records.
- semantica/conflicts/conflict_resolver.py and semantica/context/decision_recorder.py: resolution and decision recording.

Rebuild: python3 output/diagram-design/build.py
Render: node output/diagram-design/render.cjs

Style tokens: paper #ffffff; ink #202b34; muted #566773; blue #2463ad; teal #167c75; borders #cbd5dc. Font: PingFang SC with Microsoft YaHei and Arial fallbacks. All layouts preserve aspect ratio without stretched text.
