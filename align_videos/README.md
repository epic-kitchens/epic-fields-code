# Alignment (Registration) of multiple models


Registration is stored as a 3x3 rotation applying to col-vec, 1x3 translation and scalar scale.
`aligned_model = model * s * R.T + transl`

e.g.
```projects/registration/P04A/P04A.json
[
    {
        "model_vid": "P04_01",
        "rot": [
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0
        ],
        "transl": [0.0, 0.0, 0.0],
        "scale": 1.0
    }
]
```
