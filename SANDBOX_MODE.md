# Sandbox Mode Feature

## Overview
The NBA Standings Tracker now includes a **Sandbox Mode** that allows you to dynamically reassign teams to different people and see how the standings would change. This is a temporary, client-side only feature - no changes are persisted to disk and everything resets when you refresh the page.

## How to Use

### 1. Enter Sandbox Mode
- Look for the **"🎮 Enter Sandbox Mode"** button in the bottom right corner of the page
- Click it to activate sandbox mode
- The page will show a pink "SANDBOX MODE" badge at the top of the standings table
- The button changes to **"🏠 Exit Sandbox Mode"** (green)

### 2. Edit Team Assignments
- Once in sandbox mode, you'll see **"✏️ Edit Teams"** buttons next to each person's name in the Team Breakdown section
- Click the button to open a team selector with 4 dropdown menus
- Select different teams from the dropdowns (all 30 NBA teams are available)
- Each person must have exactly 4 unique teams

### 3. Save Changes
- Click **"💾 Save"** to apply your changes
- The standings table and all statistics will update instantly to reflect the new team assignments
- You can edit multiple people's teams and see the cumulative effects

### 4. Cancel Edits
- Click **"❌ Cancel"** if you change your mind about an edit
- The editor will close without making changes

### 5. Exit Sandbox Mode
- Click **"🏠 Exit Sandbox Mode"** or simply refresh the page
- All changes are discarded and the original team assignments are restored
- The page returns to showing the actual draft assignments

## Features

### Real-time Recalculation
When you change team assignments, the system automatically recalculates:
- Total wins and losses for each person
- Win percentage
- Point differential per game
- Games remaining
- Rankings
- Elimination status

### Validation
- Ensures each person has exactly 4 teams
- Prevents assigning the same team twice to one person
- Validates all selections before applying changes

### Visual Indicators
- **Pink border** around the standings table when in sandbox mode
- **Pink badge** showing "🎮 SANDBOX MODE" at the top
- **Color-coded buttons** (pink for sandbox mode, green when active)

## Technical Implementation

### Backend API Endpoints

#### `/api/teams` (GET)
Returns list of all NBA teams and current assignments
```json
{
  "status": "success",
  "teams": ["Lakers", "Warriors", ...],
  "current_assignments": {
    "JJ": ["Thunder", "Spurs", "Pistons", "Pelicans"],
    ...
  }
}
```

#### `/api/recalculate` (POST)
Recalculates standings with custom team assignments
```json
// Request
{
  "team_assignments": {
    "JJ": ["Lakers", "Warriors", "Celtics", "Heat"],
    "Andy": ["Thunder", "Spurs", "Pistons", "Pelicans"],
    ...
  }
}

// Response
{
  "status": "success",
  "sorted_friends": [...],
  "team_breakdown": {...}
}
```

### Frontend State Management
- Uses JavaScript to maintain temporary state
- Stores original data on page load
- Tracks current assignments in memory
- Updates DOM dynamically without page refresh

## Use Cases

1. **"What If" Scenarios**: 
   - "What if I had drafted the Lakers instead of the Pelicans?"
   - "How would the standings look if we redrafted?"

2. **Strategy Planning**:
   - Test different team combinations
   - Analyze which teams contribute most to win totals

3. **Draft Analysis**:
   - Compare your draft picks to alternative selections
   - See optimal draft strategies in hindsight

4. **Just For Fun**:
   - Give yourself all the best teams and dominate
   - Create worst-case scenarios
   - Play around with different combinations

## Notes

- Changes are **session-only** and never saved to the server
- Refreshing the page resets everything to the actual draft
- Historical data (win % graph) is not recalculated in sandbox mode
- Today's/Yesterday's games sections remain unchanged
- The feature is completely safe - you cannot accidentally break the real data

## Limitations

- Cannot change the total number of teams per person (fixed at 4)
- Cannot add or remove people
- Historical trend chart uses original data (not recalculated)
- No undo/redo functionality (use Cancel or Exit Sandbox Mode)

Enjoy experimenting with different team combinations! 🎮🏀
