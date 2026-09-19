ROBOT_DRAWING_PROMPT = """
You are creating a drawing plan for a simple pen-plotting robot from the attached reference
photo. Analyze the photo silently, then return only one newly rendered image.

Subject selection:
- Choose exactly one dominant, recognizable subject.
- Prefer the clearest person or animal. If neither is prominent, choose the largest obvious
  foreground object.
- Ignore every other person, object, surface, shadow, reflection, and background element.

Drawing requirements:
- Redraw only the chosen subject, centered and fully contained on a plain pure-white canvas.
- Use only solid black and solid white. Do not use gray, color, transparency, shading, gradients,
  texture, hatching, stippling, or photographic detail.
- Use bold, smooth, continuous black outlines with a consistent heavy line weight.
- Keep the outer silhouette complete. Add only the few interior lines needed for recognition.
- Remove tiny details and simplify complicated shapes into clean curves and basic forms.
- Avoid large solid-black regions unless a small filled shape is essential to recognition.
- Do not add text, labels, frames, scenery, ground lines, decorative marks, or a cast shadow.

Recognition rules:
- For a person, preserve the face shape, hair silhouette, and the most distinctive visible traits,
  such as glasses, facial hair, eyebrows, eye shape, nose, or smile. Keep the result recognizable
  as that person without adding skin texture or fine facial lines.
- For an animal, preserve the species-defining silhouette, head shape, ears, markings, and pose,
  using as few strokes as possible.
- For an object, preserve its iconic outline, proportions, orientation, and a few essential parts.

The result must look like a clean coloring-book outline that a physical robot can reproduce with
short, deliberate pen paths. Return the image only, with no explanation or caption.
""".strip()
