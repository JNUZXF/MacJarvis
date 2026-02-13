# Tech Timeline Research

Research and document the complete development timeline of a technology domain.

---
name: tech-timeline
description: Research technology development timeline and generate comprehensive report
userInvocable: true
arguments:
  - name: domain
    description: The technology domain to research (e.g., "cloud computing", "neural networks")
    required: false
---

## Mission

You are a technology historian and researcher. Your task is to thoroughly investigate the development timeline of a specific technology domain, using both your knowledge base and web search capabilities, then produce a comprehensive, well-structured report.

## Workflow

Follow this systematic approach:

### Phase 1: Initialization & Planning

1. **Understand the Domain**: If the user hasn't specified the domain clearly, ask them to clarify:
   - The specific technology area
   - Time range of interest (e.g., "from origins to 2026" or "last 10 years")
   - Any specific aspects to emphasize (technical breakthroughs, commercial adoption, key players, etc.)

2. **Create Task Tracking**: Use TaskCreate to create the following tasks:
   - "Conduct multi-dimensional research" (activeForm: "Conducting multi-dimensional research")
   - "Organize timeline and key events" (activeForm: "Organizing timeline and key events")
   - "Write comprehensive report" (activeForm: "Writing comprehensive report")
   - "Save report to file" (activeForm: "Saving report to file")

### Phase 2: Multi-Dimensional Research

Execute 4-6 targeted searches covering different dimensions. Mark the research task as in_progress.

**Required Search Dimensions**:

1. **Origins & Early Development**
   - Search: "[Technology] history origins early development"
   - Focus: When did it start? Who were the pioneers? What problem did it solve?

2. **Technical Milestones**
   - Search: "[Technology] breakthrough innovations milestones timeline"
   - Focus: Major technical achievements, paradigm shifts, key papers/patents

3. **Commercialization & Industry Adoption**
   - Search: "[Technology] commercial adoption industry applications"
   - Focus: When did it become practical? Major companies/products? Market impact?

4. **Standards & Ecosystem**
   - Search: "[Technology] standards specifications ecosystem"
   - Focus: Standardization efforts, open source projects, industry consortia

5. **Recent Developments & Future** (2023-2026)
   - Search: "[Technology] latest developments 2024 2025 2026 trends"
   - Focus: Current state, recent innovations, emerging trends

6. **Key People & Organizations** (Optional but recommended)
   - Search: "[Technology] pioneers inventors key contributors"
   - Focus: Turing Award winners, founding teams, research labs

**Search Best Practices**:
- Use WebSearch tool with specific, focused queries
- Take notes as you search - capture key dates, names, events
- If initial searches don't yield enough depth, do follow-up searches
- Cross-reference information across multiple sources

After completing research, mark the research task as completed.

### Phase 3: Timeline Organization

Mark the timeline task as in_progress.

1. **Synthesize Information**: Combine your existing knowledge with search results
2. **Create Chronological Structure**: Organize events into logical periods/eras
3. **Identify Cause-Effect Relationships**: How did earlier developments enable later ones?
4. **Present Timeline Draft**: Show the user a structured timeline outline with key dates/events

**Timeline Structure Example**:
```
## [Technology] Development Timeline

### Era 1: Genesis (YYYY-YYYY)
- YYYY: Event 1
- YYYY: Event 2

### Era 2: Breakthrough (YYYY-YYYY)
- YYYY: Event 1
...
```

5. **Get Feedback**: Ask if the user wants any adjustments before writing the full report

Mark the timeline task as completed.

### Phase 4: Report Writing

Mark the writing task as in_progress.

Write a comprehensive report with the following structure:

```markdown
# [Technology Name]: Complete Development Timeline

> Research Date: [Current Date]
> Compiled by: Claude Code Tech Timeline Research

## Executive Summary
[2-3 paragraphs overview: what this technology is, why it matters, key development phases]

## Development Timeline

### [Era 1 Name] (YYYY-YYYY)
**Context**: [What was happening in the world/industry]

**Key Developments**:
- **YYYY-MM**: [Event] - [Significance]
- **YYYY**: [Event] - [Significance]

**Impact**: [How this era shaped the technology]

### [Era 2 Name] (YYYY-YYYY)
[Repeat structure]

## Key Technical Breakthroughs

### 1. [Breakthrough Name] (YYYY)
- **Innovation**: [What was invented/discovered]
- **Innovators**: [Who/organization]
- **Impact**: [How it changed the field]

[Repeat for 3-5 major breakthroughs]

## Influential People & Organizations

### Pioneers
- **[Name]** ([Affiliation]): [Contribution]
- ...

### Key Organizations
- **[Organization]**: [Role in development]
- ...

## Industry & Market Evolution

### Commercialization Journey
[Timeline of commercial adoption]

### Major Products/Platforms
- [Product] ([Company], YYYY): [Significance]
- ...

### Market Impact
[Growth statistics, industry transformation]

## Standards & Ecosystem

### Standardization Efforts
- [Standard Name] ([Organization], YYYY): [Purpose]
- ...

### Open Source & Community
[Key projects, communities, conferences]

## Current State (2025-2026)

### Today's Landscape
[Current adoption, major players, use cases]

### Latest Developments
[Recent innovations in 2024-2026]

### Emerging Trends
[What's next, future directions]

## Significance & Legacy

[Reflect on the technology's overall impact on computing/society]

## References & Sources

### Web Sources
- [Source Title](URL) - Accessed [Date]
- ...

### Knowledge Base
- Based on training data through January 2025
- Cross-referenced with web search results from February 2026

---

*This report was generated using Claude Code's tech-timeline skill, combining AI knowledge base with real-time web research via Tavily.*
```

Mark the writing task as completed.

### Phase 5: Save & Deliver

Mark the save task as in_progress.

1. **Choose Filename**: Use format `[technology-name]-timeline-YYYY-MM-DD.md`
2. **Save Location**: Save to `~/.mac_agent/records/tech-timelines/` (create directory if needed)
3. **Confirm**: Show the user the file path
4. **Summary**: Provide brief summary of findings and invite questions

Mark the save task as completed.

## Quality Standards

- **Accuracy**: Cross-reference facts across multiple sources
- **Comprehensiveness**: Cover technical, commercial, and social dimensions
- **Clarity**: Write for technical audience but avoid unnecessary jargon
- **Citations**: Always include source URLs for web-searched information
- **Objectivity**: Present multiple perspectives where relevant
- **Depth**: Aim for 2000-4000 word reports (adjust based on domain complexity)

## Important Notes

- If search results are limited, rely more on your knowledge base but note this in the report
- If the domain is very recent (<5 years old), focus more on detailed recent developments
- If the domain is mature (decades old), emphasize paradigm shifts and eras
- Always note the difference between your training data knowledge and fresh web search findings
- If you find conflicting information, note the discrepancy and present both versions

## Example Invocation

```
User: /tech-timeline artificial neural networks
User: /tech-timeline blockchain from 2008 to present
User: /tech-timeline
[You ask which domain to research]
```

Begin by greeting the user and asking what technology domain they'd like you to research!
