# Hampy design system

## Intent
Hampy is a phone-first food-bank volunteer tool: warm, capable, and dependable rather than consumer-shopping styled. Inventory is primary; asking the robot is prominent secondary work. Dials: variance 4, motion 3, density 5. The baseline adapts restrained food-service hierarchy with finance-grade form clarity, without copying brand assets or trademarks.

## Tokens
| Role | Value | Use |
| --- | --- | --- |
| `background` | `#F7F9F5` | App canvas |
| `surface` | `#FFFFFF` | Cards & fields |
| `surface-muted` | `#EAF1E8` | Secondary groups |
| `action` | `#1D5C3B` | Primary actions |
| `action-pressed` | `#16462D` | Pressed primary controls |
| `ink` | `#16231A` | Copy |
| `muted` | `#5B6A5D` | Supporting copy |
| `line` | `#D5E0D4` | Boundaries |
| `danger` | `#A43D2E` | Errors & removal |

Use action with white text only. No gradients, purple/blue AI effects, or second bright accent.

## Type & layout
Platform sans stack (SF Pro / Roboto / system) ensures Expo Go reliability. Title 30/36 semibold; section 20/26 semibold; card 17/23 semibold; body 16/23; label 13/18 semibold. Use a 4-point rhythm, 16–24 px phone gutters, and 680 px max content width on web.

## Components & states
Cards: 16 px radius, one-pixel `line` boundary, green-tinted elevation only for hierarchy. Buttons are pills; inputs have 12 px radii. Controls are 48 px minimum with visible focus and pressed states. Loading mirrors shelf cards; empty/error states preserve context and offer a next action. Motion is 160–220 ms opacity/transform only and removed under reduced motion.

## Guardrails
Do keep headings left aligned, language active, and destructive actions explicit. Don’t use decorative food photos, generic dashboard stats, unsupported “voice AI” claims, dense tables, or unlabeled icon actions.
