# The Night the Jellyfish Came to the City

Entry for make.fun `coolest-art-01`: a program that draws one piece of art.

## What it draws

A giant luminous jellyfish drifts over a tiny neon city skyline at night —
one clear focal point, a bold teal/magenta palette, clean poster style, no
text. Two small distant jellyfish give the scene depth. The image is drawn
entirely in code (pure Python standard library: `zlib` + `struct` PNG
encoder), so it is original work, not a copy of any photograph or artwork.

## Run

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py   # writes out/entry.png (1024x1024, ~62 KB)
```

Deterministic: running it twice writes byte-identical files.
No network, no third-party packages, no secrets.

## License

MIT — see `LICENSE`.
