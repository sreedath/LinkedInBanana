---
name: linkedin-article
description: Defines the structure, pacing, and format for LinkedIn articles (long-form educational posts). Use this skill whenever generating a LinkedIn article that explains a technical concept, shares a framework, or teaches something. This skill works alongside the writing-preferences skill, which handles tone, punctuation, and word choice rules.
---

# LinkedIn Article Structure

This skill defines the structural blueprint for LinkedIn articles. It is based on a reference article that represents the target quality. Every LinkedIn article generated must follow this structure unless the user explicitly overrides it.

The writing-preferences skill handles tone, contractions, em dashes, emojis, and paragraph length. This skill handles article architecture: how to open, how to build the body, how to close, and how to pace the explanation.

---

## Article Architecture

Every LinkedIn article has exactly four sections, in this order:

1. Opening hook (1 paragraph)
2. Numbered body sections (3 to 5 sections)
3. Closing distillation (1 paragraph)
4. Call to action (1 to 2 sentences)

Total length should be 400 to 700 words. LinkedIn articles should not be essays. They should feel like a focused, well-paced explanation that respects the reader's time.

---

## Section 1: Opening Hook

The opening is exactly one paragraph of 2 to 3 sentences. It does two things:

1. Acknowledges a relatable pain point or common perception about the topic.
2. Immediately reframes it with a "but actually, the core idea is simple" pivot.

The goal is to make the reader feel like they are about to understand something they previously found intimidating or confusing. Do not open with a definition. Do not open with a question. Open with an honest acknowledgment followed by a reassuring reframe.

**Pattern:**

> [Topic] looks [intimidating/complex/overwhelming] at first because [specific reasons]. However, at its core, [topic] is built on [simple idea], and once that clicks, the rest starts making sense.

**Reference example:**

> Diffusion models look intimidating mathematically on first contact because they come with long equations, UNets, and many Greek letters if you look at the paper. However, at its core, a DDPM is built on an intuitive idea, and once that idea clicks, the entire model starts making sense.

---

## Section 2: Numbered Body Sections

The body consists of 3 to 5 numbered sections. Each number represents one logical step in understanding the concept. The sections must follow a progressive construction pattern: each one builds directly on the previous.

### Rules for numbered sections:

- Each section is one paragraph of 3 to 6 sentences.
- Each section carries exactly one idea or one logical step.
- The first sentence of each section states what this step is about.
- The rest of the sentences explain, clarify, or give the intuition behind it.
- Use plain language to explain technical ideas. Write as if explaining to a smart person who does not have this specific background yet.
- Do not front-load jargon. Introduce a term only after the reader already understands the concept it refers to.

### Progressive construction pattern:

The numbered sections must follow a logical chain. Common progressions include:

- **Process walkthrough:** Step 1 of the process, then Step 2, then Step 3, until the full picture is assembled.
- **Problem-solution layering:** Simple version of the idea, then why it is incomplete, then the fix, then the next layer.
- **Destruction-to-creation:** How something is broken down, then how that breakdown is reversed.

The reader should feel that each numbered section is the natural next question after the previous one. If the progression feels like a list of disconnected facts, the structure is wrong.

### Reference body structure (diffusion model article):

1. Forward diffusion: how images are intentionally destroyed by adding noise.
2. Reverse process: the neural network learns to predict noise, not generate images.
3. Timestep encoding: how the model adapts its behavior based on the noise level.
4. Generation: starting from pure noise and iteratively denoising to produce an image.

Each section answers the question that the previous section implicitly raises.

---

## Section 3: Closing Distillation

The closing is exactly one paragraph of 2 to 4 sentences. It serves one purpose: distill the entire article into a single memorable insight.

### Rules:

- Start with a framing phrase like "If I had to explain [topic] in one line" or "The core insight is this."
- State the one-line distillation clearly.
- Follow it with one sentence that reframes the reader's perspective. The reader should walk away feeling that the topic is no longer intimidating.

**Pattern:**

> If I had to explain [topic] in one line, I would say this: [one-line distillation]. Once you see it this way, [topic] stops feeling like [intimidating thing] and starts feeling like [accessible reframe].

**Reference example:**

> If I had to explain DDPM in one line, I would say this: a diffusion model learns how to undo noise, not how to draw images, and by learning this simple skill extremely well, it ends up learning the entire data distribution. Once you see it this way, DDPMs stop feeling like magic and start feeling like a very elegant application of probability and neural networks working together.

---

## Section 4: Call to Action

The call to action is 1 to 2 sentences at the very end. It links to a relevant resource (article, video, series, newsletter) and invites the reader to engage.

### Rules:

- Keep it brief and direct.
- Reference the broader series or context if one exists.
- Include a link if applicable.
- Do not use emojis or hashtags.

**Reference example:**

> In this week's Transformers for vision series, we discuss diffusion models. Details here: [link]

---

## Pacing and Rhythm

### Sentence variety

Mix short and medium sentences. A short declarative sentence followed by a longer explanatory one creates good rhythm. Do not write three long sentences in a row.

**Good:** "That is all the UNet is trained to do. It does not generate pixels, it does not hallucinate images, it only predicts noise."

**Bad:** "The UNet is trained to predict the noise that is present in a given noisy image at a particular timestep, and it does this by taking the noisy image and the timestep as inputs and outputting an estimate of the noise component."

### Emphasis through simplification

When making a key point, use a short, punchy sentence that strips away all complexity. This is how you make ideas stick.

Examples from the reference article:
- "That is all the UNet is trained to do."
- "Nothing is learned in this phase."
- "It only predicts noise."

### Transitions between numbered sections

Each numbered section should feel like a natural continuation. Use implicit or explicit transition cues:

- "Once we understand [previous concept], the real question becomes..."
- "The [new concept] itself matters a lot, because..."
- "During [next phase], we start from..."

Do not use generic transitions like "Next" or "Moving on" or "Additionally."

---

## What LinkedIn Articles Must Never Do

- Never open with a definition or a dictionary-style explanation.
- Never use bullet points inside the body. The numbered sections replace bullets.
- Never exceed 5 numbered sections. If the topic needs more, it should be split into multiple articles.
- Never include hashtags.
- Never include emojis.
- Never end without a call to action.
- Never write paragraphs longer than 6 sentences.
- Never use filler phrases like "In today's fast-paced world" or "As we all know."
- Never use contractions or em dashes (enforced by writing-preferences skill).
- Never use these banned words: "demystifying", "delve", "dive deep", "deep dive", "unleash", "game-changer", "cutting-edge", "revolutionize", "paradigm shift", "comprehensive guide".
- Never sound like AI. Avoid the polished, generically enthusiastic tone that LLM outputs tend to have.

---

## Quick Checklist Before Submitting a LinkedIn Article

1. Does the opening acknowledge a pain point and immediately reframe it?
2. Are there 3 to 5 numbered body sections that build progressively?
3. Does each numbered section carry exactly one logical step?
4. Is there a closing distillation paragraph that summarizes the core insight in one line?
5. Does the article end with a clear call to action?
6. Is the total length between 400 and 700 words?
7. Are all writing-preferences rules followed (no contractions, no em dashes, no emojis, short paragraphs)?
8. Does the article feel like a focused explanation, not an essay or a listicle?

If any answer is no, revise before presenting to the user.
