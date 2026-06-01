# Question-Analysis Annotation Rubric

This rubric documents the per-turn fields stored by projects whose
`annotation_type` is `question_analysis`.

## Fields per turn (one row per `message_id` + `annotator_id`)

| Field            | Type    | Description                                                                  |
|------------------|---------|------------------------------------------------------------------------------|
| `label`          | string  | Free-form turn-grouping label, semantically like a thread id.                |
| `trigger_marker` | boolean | True when the turn is unambiguously question-form (see rubric below).        |
| `borderline`     | boolean | True when the case is fronteiriço / ambiguous.                               |
| `multiform`      | boolean | True when the turn mixes multiple question-form features.                    |

## `trigger_marker` rubric

A turn is question-form if its **surface wording is unambiguously
interrogative**. Mark only forms that cannot reasonably be read as
non-questions. Do not mark a turn merely because it *could* be heard as a
question with the right intonation or context.

The check has two steps: the question mark is the primary check, and the
no-question-mark features are the secondary band.

### Primary check — the question mark

If the turn carries a question mark, it is question-form. This is the main,
high-frequency path.

### Secondary band — no question mark

WhatsApp-style group chat often omits punctuation, so a turn with no question
mark can still be unambiguously interrogative in its wording. A no-question-mark
turn is question-form if it carries one of the five features below. Each
feature comes with an exclusion — the exclusion is what makes the feature
reliable enough to settle the turn for sure.

1. **Bare interrogative fragment.** The whole turn is an interrogative pro-form
   or a short interrogative phrase — "Porquê", "Como assim", "Qual deles",
   "Em que sentido". No declarative reading exists; no exclusion is needed.

2. **Turn-initial interrogative wh-word.** A wh-word — *quem, o que / o quê,
   qual, quando, onde, como, porquê, quanto* — opens the turn in matrix
   interrogative use: "Como definimos beleza", "Quem disse isso". *Does not
   count* when the wh-word is relative ("a forma *como* pensamos") or embedded
   under a verb of saying, thinking, or knowing ("não sei *o que* pensar").

3. **Dedicated interrogative construction.** The *será que…* / *não será (que)…*
   frame, or subject–verb inversion where it occurs: "Será que a beleza é
   universal", "Não será isso cultural". *Does not count* when *será* is a
   plain future declarative ("isso *será* difícil") — the signal is the
   *será que* / *(não) será + X* frame, not the word *será* on its own.

4. **Disjunctive choice question.** The turn presents a choice between
   alternatives as its point: "Universal ou diversa", "Concordas ou discordas".
   *Does not count* when *ou* is additive or hedging ("ou pelo menos…",
   "duas ou três").

5. **Conventionalised answer-soliciting formula.** The turn matches a recognised
   question formula — "alguém sabe…", "o que acham", "quem concorda",
   "podem explicar". Keep this a closed list, confirmed against actual DebaQi
   turns; do not extend it case by case.

## Inter-annotator agreement (IAA)

For `question_analysis` projects the IAA combines:

- **Label one-to-one accuracy** — Hungarian-algorithm matching on the `label`
  field, identical to disentanglement projects (0–100).
- **Trigger / borderline / multiform agreement** — percentage of common
  messages where the boolean matches (0–100).
- **Combined IAA** — unweighted mean of the four metrics above.

Only messages annotated by **both** annotators contribute to the per-pair
metric (`common_message_count` is reported alongside).
