import genanki
from pathlib import Path

def export_to_anki(glossary: dict, output_path: Path):
    """Convert glossary.json into an Anki .apkg file."""
    # Unique model and deck IDs (stable across runs)
    model_id = 1607392319
    deck_id = 2059400110
    
    my_model = genanki.Model(
        model_id,
        'Subtitle Forge CFA Vocabulary',
        fields=[
            {'name': 'English'},
            {'name': 'Chinese'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': '<div style="font-size: 24px; text-align: center; font-weight: bold;">{{English}}</div>',
                'afmt': '{{FrontSide}}<hr id="answer"><div style="font-size: 20px; color: #2c3e50; text-align: center;">{{Chinese}}</div>',
            },
        ],
        css='.card { font-family: arial; font-size: 20px; text-align: center; color: black; background-color: white; }'
    )

    my_deck = genanki.Deck(deck_id, 'CFA Exam :: Subtitle Forge Terms')

    count = 0
    for eng, data in glossary.items():
        val = data.get("val", "") if isinstance(data, dict) else data
        if not eng or not val: continue
        
        note = genanki.Note(
            model=my_model,
            fields=[str(eng), str(val)]
        )
        my_deck.add_note(note)
        count += 1

    if count > 0:
        genanki.Package(my_deck).write_to_file(str(output_path))
        print(f"  [Anki] Exported {count} cards to {output_path.name}")
    else:
        print("  [Anki] Glossary is empty. Nothing to export.")
