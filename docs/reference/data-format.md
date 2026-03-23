# Data Format

## CSV Input

Chat rooms are imported via CSV. Each row represents one turn in the conversation.

```csv
turn_id,user_id,turn_text,reply_to_turn
T001,alice,"Hello everyone",
T002,bob,"Hi! How are you?",T001
T003,alice,"Doing well, thanks!",T002
T004,carol,"What are we discussing today?",
```

| Column | Required | Description |
|---|---|---|
| `turn_id` | ✅ | Unique identifier for the turn within the room |
| `user_id` | ✅ | Speaker identifier |
| `turn_text` | ✅ | Turn content |
| `reply_to_turn` | ❌ | `turn_id` of the turn being replied to; leave empty if none |

!!! tip
    A sample file is provided at [`docs/sample_chat_room.csv`](../sample_chat_room.csv).

### Validation rules

- `turn_id` must be unique within each CSV file.
- `reply_to_turn`, if set, must reference a `turn_id` that exists in the same file.
- Empty rows and rows with missing required columns are rejected during preview.

### Multi-room import

Each CSV file maps to one chat room. To import multiple rooms into a project, upload one CSV per room.

---

## Export Formats

### Disentanglement — JSON

```json
{
  "project": "My Project",
  "room": "room-01",
  "annotator": "alice",
  "annotations": [
    { "turn_id": "T001", "thread_id": "A" },
    { "turn_id": "T002", "thread_id": "A" },
    { "turn_id": "T003", "thread_id": "B" }
  ]
}
```

One JSON file is produced per annotator per room.

### Adjacency Pairs — ZIP

The export is a ZIP archive containing one plain-text file per annotator per room. Each line encodes one directed link:

```
T002 -> T001 [question-answer]
T004 -> T001 [topic-shift]
```

Format: `<from_turn_id> -> <to_turn_id> [<relation_type>]`
