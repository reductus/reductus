template = {
    "modules": [
    {
      "module": "ncnr.refl.super_load",
      "title": "load spec",
      "config": {"intent": ["specular"]},
      "module_id": 0,
      "x": 50,
      "y": 30
    },
    {
      "module": "ncnr.refl.mask_points",
      "title": "mask",
      "module_id": 1,
      "x": 190,
      "y": 30
    },
    {
      "module": "ncnr.refl.join",
      "title": "join",
      "module_id": 2,
      "x": 330,
      "y": 30
    },
    {
      "module": "ncnr.refl.super_load",
      "title": "load bg+",
      "config": {"intent": ["background+"]},
      "module_id": 3,
      "x": 50,
      "y": 70
    },
    {
      "module": "ncnr.refl.mask_points",
      "title": "mask",
      "module_id": 4,
      "x": 190,
      "y": 70
    },
    {
      "module": "ncnr.refl.super_load",
      "title": "load bg-",
      "config": {"intent": ["background-"]},
      "module_id": 5,
      "x": 50,
      "y": 110
    },
    {
      "module": "ncnr.refl.mask_points",
      "title": "mask",
      "module_id": 6,
      "x": 190,
      "y": 110
    },
    {
      "module": "ncnr.refl.join",
      "title": "join",
      "module_id": 7,
      "x": 330,
      "y": 110
    },
    {
      "module": "ncnr.refl.join",
      "title": "join",
      "module_id": 8,
      "x": 330,
      "y": 70
    },
    {
      "module": "ncnr.refl.super_load",
      "title": "load slit",
      "config": {"intent": ["intensity"]},
      "module_id": 9,
      "x": 50,
      "y": 150
    },
    {
      "module": "ncnr.refl.mask_points",
      "title": "mask",
      "module_id": 10,
      "x": 190,
      "y": 150
    },
    {
      "module": "ncnr.refl.subtract_background",
      "title": "sub bg",
      "module_id": 11,
      "x": 470,
      "y": 30
    },
    {
      "module": "ncnr.refl.rescale",
      "title": "rescale",
      "module_id": 12,
      "x": 330,
      "y": 150
    },
    {
      "module": "ncnr.refl.join",
      "title": "join",
      "module_id": 13,
      "x": 470,
      "y": 150
    },
    {
      "module": "ncnr.refl.divide_intensity",
      "title": "divide",
      "module_id": 14,
      "x": 615,
      "y": 70
    }
  ],
  "wires": [
    {
      "source": [
        0,
        "output"
      ],
      "target": [
        1,
        "data"
      ]
    },
    {
      "source": [
        1,
        "output"
      ],
      "target": [
        2,
        "data"
      ]
    },
    {
      "source": [
        2,
        "output"
      ],
      "target": [
        11,
        "data"
      ]
    },
    {
      "source": [
        3,
        "output"
      ],
      "target": [
        4,
        "data"
      ]
    },
    {
      "source": [
        4,
        "output"
      ],
      "target": [
        8,
        "data"
      ]
    },
    {
      "source": [
        8,
        "output"
      ],
      "target": [
        11,
        "backp"
      ]
    },
    {
      "source": [
        5,
        "output"
      ],
      "target": [
        6,
        "data"
      ]
    },
    {
      "source": [
        6,
        "output"
      ],
      "target": [
        7,
        "data"
      ]
    },
    {
      "source": [
        7,
        "output"
      ],
      "target": [
        11,
        "backm"
      ]
    },
    {
      "source": [
        9,
        "output"
      ],
      "target": [
        10,
        "data"
      ]
    },
    {
      "source": [
        10,
        "output"
      ],
      "target": [
        12,
        "data"
      ]
    },
    {
      "source": [
        12,
        "output"
      ],
      "target": [
        13,
        "data"
      ]
    },
    {
      "source": [
        13,
        "output"
      ],
      "target": [
        14,
        "base"
      ]
    },
    {
      "source": [
        11,
        "output"
      ],
      "target": [
        14,
        "data"
      ]
    }
  ]
}
