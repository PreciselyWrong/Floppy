# Branding

Authenticated users choose one navigation identity in Settings > Preferences:
the original colour logo, the monochrome logo, an editable text wordmark, a
custom image, or a visually hidden logo. The shared
`users/components/brand_logo.html` template is the single renderer used by the
authenticated shell, public shell, and sign-in layout.

Hidden branding keeps a labelled home link for keyboard and screen-reader
users. Text is escaped by Django and limited to 32 characters.

Custom images accept PNG, JPEG, and WebP uploads up to 2 MB. They are decoded,
resized within 256 by 64 pixels, and re-encoded as metadata-free WebP before
storage. SVG is intentionally rejected. The resulting data URL is capped at
40 KB so a user preference cannot become an unbounded page payload.
