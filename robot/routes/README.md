# Recorded route

Before deployment, copy the existing robot file without modifying it:

```bash
scp bracketbot@bracketbot-0186.local:/home/bracketbot/bbapps/hampy_demo/routes/table1_to_table2.json ./table1_to_table2.json
```

Expected SHA-256 from the working robot route:

```text
ee017fa1b7549a44c92f2f0824a254366a0c8e8534b84565eabae7a14cc98802
```

Verify it after copying:

```bash
shasum -a 256 table1_to_table2.json
```
