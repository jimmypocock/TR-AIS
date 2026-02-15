# ChatM4L UI Design

## Layout

```
┌─────────────────────────────────────────┬────┐
│                                         │ ⚙️ │ Settings
│                                         ├────┤
│           Main Content Area             │ 🎯 │ Skills
│         (Chat / Settings / etc)         ├────┤
│                                         │ 👤 │ Profile
│                                         ├────┤
│                                         │ ❓ │ Help
├─────────────────────────────────────────┼────┤
│  Chat Input                             │ ➤  │ Send
└─────────────────────────────────────────┴────┘
```

## Color Palette (Ableton Style)

| Element | Color | Hex |
|---------|-------|-----|
| Background | Dark Grey | `#3D3D3D` |
| Input Background | Black | `#1A1A1A` |
| Dividers | Darker Grey | `#2A2A2A` |
| Text Primary | White | `#FFFFFF` |
| Text Secondary | Light Grey | `#B3B3B3` |
| Accent Active | Orange | `#F5A623` |
| Accent Secondary | Blue | `#50C8FF` |

## Views

### 1. Chat (Default)

- Scrollable chat history
- Format: "You: message" / "AI: response"
- Input field active

### 2. Settings

```
Provider: anthropic
Model: claude-sonnet-4-20250514

Config: ~/Library/Application Support/ChatM4L/

[Reload Config]  [Open Folder]
```

### 3. Skills

```
Available Skills:
● drums        [Active]
○ mixing
○ sound-design

[Deactivate Skill]
```

### 4. Profile

```
User Profile

Edit core/user.md to personalize ChatM4L.

Status: Not configured
        (or shows summary if configured)

[Open Profile]
```

### 5. Help

```
Commands:
/help      - Show commands
/status    - Show status
/newchat   - Clear conversation
/reload    - Reload config
/skills    - List skills
/<skill>   - Activate skill

Tip: Just type naturally to chat!
```

## Max Objects

### Main Content Area

- `panel` - Background (#3D3D3D)
- `jsui @filename ui/chat-display.js` - Chat display (scrollable, alternating colors)
- `textedit` - Static content (settings, skills, profile, help - readonly)

The jsui and textedit occupy the same space - bridge.js toggles visibility.

### Chat Input

- `panel` - Input background (#1A1A1A)
- `textedit` - Input field (editable, 2 lines)

### Sidebar

- `panel` - Sidebar background (#3D3D3D)
- `live.text` x4 - Icon buttons (Settings, Skills, Profile, Help)
- `live.text` - Send button

### Dividers

- `panel` objects - 1-2px wide, color #2A2A2A

## Bridge.js Updates

### Outlets

```javascript
outlets = 5;

const OUT_NODE = 0;      // To node.script
const OUT_CHAT = 1;      // To jsui chat display
const OUT_STATIC = 2;    // To textedit (settings, help, etc)
const OUT_SIDEBAR = 3;   // To sidebar (button states)
const OUT_INPUT = 4;     // To input field visibility
```

### View State

```javascript
let currentView = "chat";  // chat | settings | skills | profile | help
```

### New Handlers

```javascript
function setView(viewName) { ... }
function refreshView() { ... }
function getSettingsContent() { ... }
function getSkillsContent() { ... }
function getProfileContent() { ... }
function getHelpContent() { ... }
```

## Interaction Flow

1. User clicks sidebar button (e.g., Skills)
2. Button sends `setView skills` to bridge.js
3. bridge.js updates `currentView`, calls `refreshView()`
4. `refreshView()` generates content for that view
5. Content sent to OUT_CONTENT outlet
6. Sidebar state updated (highlight active button)

## Size Considerations

- Minimum width: ~400px (chat needs room)
- Minimum height: ~300px
- Sidebar: 40px wide
- Input area: 50px tall

---

## Max Patch Wiring Guide

### v8 Object Setup

```
[v8 code/bridge.js @autowatch 1]
    |      |      |      |      |
    0      1      2      3      4
    |      |      |      |      |
  node   chat  static sidebar input
```

### Outlet Connections

**Outlet 0 → node.script**
```
[v8] outlet 0
      |
[node.script code/ai/main.js]
```

**Outlet 1 → Chat Display (jsui)**
```
[v8] outlet 1
      |
[route message clear bang visible]
   |       |      |       |
   |       |      |    [t set $1]
   |       |      |       |
   └───────┴──────┴───────┘
                  |
[jsui @filename ui/chat-display.js @size 400 250]

Messages:
  message <sender> <text>  - Add chat message
  clear                    - Clear all messages
  bang                     - Redraw
  visible <0|1>            - Show/hide
```

**Outlet 2 → Static Content (textedit)**
```
[v8] outlet 2
      |
[route set visible]
   |       |
   |    [t set $1]
   |       |
   └───────┘
        |
[textedit] (readonly - for settings, skills, profile, help)
```

**Outlet 3 → Sidebar Buttons**
```
[v8] outlet 3
      |
[route 0 1 2 3 -1]
  |   |   |   |  |
 set set set set (none)
  |   |   |   |
(highlight buttons 0-3, -1 = chat view, no highlight)
```

**Outlet 4 → Input Area**
```
[v8] outlet 4
      |
[sel 0 1]
  |     |
hide  show
  |     |
(control input visibility or enabled state)
```

### Sidebar Button Wiring

Each button sends its view name to bridge.js:

```
[live.text "⚙"] (Settings button)
      |
[sel 1]
      |
[message setView settings]
      |
[v8]

[live.text "🎯"] (Skills button)
      |
[sel 1]
      |
[message setView skills]
      |
[v8]

[live.text "👤"] (Profile button)
      |
[sel 1]
      |
[message setView profile]
      |
[v8]

[live.text "❓"] (Help button)
      |
[sel 1]
      |
[message setView help]
      |
[v8]
```

### Chat Input Wiring

```
[textedit] (input field)
      |
[route text]
      |
[prepend chat]
      |
[v8]
```

### Send Button

```
[live.text "➤"]
      |
[sel 1]
      |
[bang]
      |
[textedit] (triggers input to send)
```

### Return to Chat (clicking content area or input)

```
[textedit] (main content - on click)
      |
[message setView chat]
      |
[v8]
```

### node.script → v8 Response Routing

```
[node.script]
      |
[route response error status ready needsconfig pong chatcleared newchat]
   |       |      |      |        |        |        |         |
   |       |      |      |        |        |        |    [prepend newchat]
   |       |      |      |        |        |   [prepend chatcleared]
   |       |      |      |        |   [prepend pong]
   |       |      |      |   [prepend needsconfig]
   |       |      |   [prepend ready]
   |       |   [prepend status]
   |   [prepend error]
[prepend response]
   |
   └───────────────────────────────────────────────────────────────┐
                                                                   |
                                                                 [v8]
```

### Button Highlight Logic

Use `[live.text]` with active color properties:

- Inactive: Background `#3D3D3D`, Text `#B3B3B3`
- Active: Background `#F5A623`, Text `#FFFFFF`

The sidebar outlet sends the active button index (0-3) or -1 for chat.
Use `[sel 0 1 2 3 -1]` to route to each button's active state.

### Panel Colors (Inspector Settings)

| Panel | Background Color |
|-------|-----------------|
| Main background | `#3D3D3D` (61, 61, 61) |
| Input area | `#1A1A1A` (26, 26, 26) |
| Dividers | `#2A2A2A` (42, 42, 42) |

### Presentation Mode Layout

```
┌─────────────────────────────────────────┬──────┐
│                                         │  ⚙️  │
│                                         ├──────┤
│           [jsui] / [textedit]           │  🎯  │
│         Chat or Static Content          ├──────┤
│          (toggled by view)              │  👤  │
│                                         ├──────┤
│                                         │  ❓  │
├─────────────────────────────────────────┼──────┤
│  [textedit input]                       │  ➤   │
└─────────────────────────────────────────┴──────┘
```

Suggested dimensions:
- Total: 450 x 350 px
- Sidebar: 45 px wide
- Input row: 45 px tall
- Content area: Remaining space

---

## Chat Display (jsui)

The chat display is a custom jsui component (`ui/chat-display.js`) that provides:

### Features
- Alternating row colors for readability
- Auto text wrapping
- Mouse wheel scrolling
- Drag scrolling
- Double-click to scroll to bottom
- Different colors for user/AI/system messages
- Scrollbar indicator

### Message Types
| Sender | Background | Label Color |
|--------|------------|-------------|
| You (user) | Dark (#292929) | Orange |
| AI | Medium (#383838) | Blue |
| System | Dark (#2D2D2D) | Orange |
| Error | Red tint | Orange |

### jsui Inspector Settings
```
@filename ui/chat-display.js
@size 400 250  (or fill available space)
@autowatch 1   (for development)
```

### API (messages from bridge.js)
```javascript
message <sender> <text>  // Add a message
clear                    // Clear all messages
bang                     // Force redraw
visible <0|1>            // Show/hide (for view switching)
```

### Customization
Edit `m4l/code/ui/chat-display.js` config object:
```javascript
var config = {
    fontSize: 12,
    lineHeight: 18,
    scrollSpeed: 40,
    colors: { ... }
};
```
