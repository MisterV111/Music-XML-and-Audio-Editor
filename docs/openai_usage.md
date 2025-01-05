# OpenAI Integration Usage Guide

## Overview
The OpenAI integration allows users to input natural language commands to edit audio sections. The system interprets these commands and converts them into specific editing actions.

## Supported Commands

### Keep Sections
Keep only specific sections and remove others.
```
Examples:
- "keep only the chorus and outro"
- "keep the intro, verse 1, and chorus"
- "keep everything except verse 2"
```

### Remove Sections
Remove specific sections while keeping others.
```
Examples:
- "remove the intro"
- "remove verse 2 and bridge"
- "delete the outro section"
```

### Reorder Sections
Change the order of sections.
```
Examples:
- "move the chorus to the beginning"
- "reorder sections as: intro, chorus, verse 1, chorus"
- "put the bridge before the final chorus"
```

## Command Structure
- Commands should be clear and specific
- Use section names as they appear in the song structure
- Multiple sections can be specified using "and" or commas
- Common synonyms for actions are supported (e.g., "delete" = "remove")

## Response Format
The system will respond with:
1. Confirmation of the understood command
2. Preview of what changes will be made
3. Any error messages if the command cannot be processed

## Error Handling
Common error scenarios:
- Invalid section names
- Unclear or ambiguous commands
- Missing action or sections
- Invalid reordering sequences

## Examples with Responses

### Successful Command
Input: "keep only the chorus and outro"
Response: "Will keep the following sections: chorus, outro"

### Error Case
Input: "remove the middle part"
Response: "Some sections mentioned are not available in the song. Please use specific section names."

### Reordering
Input: "reorder as: verse 1, chorus, verse 2, chorus, outro"
Response: "Will reorder the sections as follows: verse_1 → chorus → verse_2 → chorus → outro" 