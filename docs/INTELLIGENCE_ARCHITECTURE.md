# KICK-OFF Football Intelligence Architecture

## Purpose

Build a substitution decision-support system that compares two incoming-player options in the same match context. The system must explain its evidence and uncertainty. It must not present observational associations as causal effects.

## Core decision context

Each comparison is conditioned on:
- Match, competition and season context.
- Minute, scoreline, score state and home/away status.
- Available match importance and event-derived momentum indicators.
- Outgoing player, candidate incoming players and proposed roles.
- Team/manager tactical context, where supported by the data.

## Intelligence layers

### 1. Player identity and positional profile

Maintain a canonical player table keyed by Wyscout player ID, joined to the public player metadata. Preserve source fields and record missingness.

Represent position at three distinct levels:
- **Primary/natural position:** source-listed position, if supplied.
- **Observed positions:** positions actually recorded in lineups or event/match data.
- **Proposed role:** the role selected for the substitution scenario.

Derive likely positional flexibility only from repeated observed deployment. Do not infer a natural position from a single appearance. Show evidence counts and confidence, and flag unfamiliar roles as positional-adaptation risk.

### 2. Player playstyle

Create event-derived indicators only where the event schema supports them, for example:
- Passing volume, completion and progression.
- Carries/dribbles and ball retention.
- Chance creation and shooting.
- Defensive duels, interceptions, recoveries and pressing proxies.
- Turnovers and errors, where consistently defined.

Normalize rates by minutes or relevant opportunities. Separate raw counts from rates. Avoid calling an event proxy a direct measurement of an underlying trait.

### 3. Tactical ideology and role compatibility

Represent tactical approaches as continuous, evidence-backed dimensions rather than mutually exclusive labels:
- Positional occupation / Juego de Posición.
- Counterpressing / Gegenpress.
- High press.
- Mid-block and low-block compactness.
- Possession circulation and progression.
- Direct play and counter-attacking.

Infer team/manager tendencies from repeated team-match observations, not reputation or a single match. Each dimension must have documented feature definitions, sample size and uncertainty. A manager can exhibit multiple tendencies and change approach by opponent or game state.

### 4. Pressure and composure proxies

Composure is not directly observable in event data. KICK-OFF will therefore report **performance-under-pressure proxies**, not psychological composure scores.

For players, compare pressure-context performance with their own baseline using supported indicators:
- Ball retention and passing execution.
- Turnovers and failed actions.
- Defensive action outcomes and fouls.
- Shot selection and execution.
- Late-game performance, controlling for role and match state where feasible.

Define pressure from observable context (minute, score state, scoreline, competition stage and event pressure/momentum proxies where available). Do not use minute alone as a pressure label.

For managers, derive decision-pattern proxies:
- Substitution timing by score state and match phase.
- Tactical/substitution response after goals conceded or scored.
- Changes in attacking/defensive personnel or roles, if detectable.
- Repeatability of decisions in comparable contexts.

These describe observed behaviour; they do not establish the manager's internal emotional state or decision quality without a suitable evaluation design.

### 5. Interactive comparison

The dashboard should let a user select:
- Match situation and score.
- Outgoing player.
- Candidate A and Candidate B.
- Proposed role for each candidate.
- Tactical approach / team context.

The comparison view should show:
- Player identity, source-listed and observed positions.
- Proposed-role fit and adaptation evidence.
- Playstyle profile.
- Tactical compatibility.
- Performance-under-pressure evidence.
- Manager/team context.
- Risks, trade-offs, sample sizes and missing data.
- Model probabilities only when a validated candidate-sensitive model is available.

A clear explanation panel should state why a factor supports or weakens each option. Missing evidence must be displayed as unknown, never silently converted to a low score.

## Data and modelling rules

1. Keep raw source data unchanged and retain attribution/licence information.
2. Build canonical player, team, coach/manager, match, lineup, event and substitution tables with stable IDs.
3. Verify which fields exist in the downloaded Wyscout files before implementing joins. Do not assume manager names or position fields are present in every file.
4. Prevent leakage: features must be available at the simulated substitution time. Future events may be used only to define outcomes or evaluate historical performance.
5. Use match-aware and chronological validation where practical. Keep all rows from the same match in one split.
6. Report class balance, macro F1, balanced accuracy, calibration and confidence intervals/sample counts where appropriate.
7. Treat the current match-state logistic regression as a baseline only. It cannot distinguish candidates because player features are not inputs.
8. Do not claim substitution causality from observational data.

## Build sequence

1. **Dataset integration:** inventory the actual downloaded player, team, match, lineup and event schemas; join player names and positions to substitution IDs; recover manager identity from the correct source table if available.
2. **Feature engineering:** build observed positional histories and event-derived playstyle features with explicit sample counts.
3. **Pressure analysis:** define pressure contexts and player/manager performance-under-pressure proxies.
4. **Tactical profiles:** calculate team/manager tendencies from repeated match observations and document each metric.
5. **Comparison interface:** build interactive A/B player cards, role selection, tactical context and clear evidence summaries.
6. **Candidate-sensitive modelling:** train and validate models only after features are joined and leakage checks pass.

## Current known limitation

The existing baseline uses only minute, score, score difference, team side and score state. Its probabilities are identical for both candidates. The current dashboard must not label one player as model-favoured until candidate-level features have been integrated and validated. The outcome labels are also provisional pending the previously identified goal-reconstruction checks.
