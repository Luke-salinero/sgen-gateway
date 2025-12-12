## Overview

This guide outlines the structure, requirements, and validation rules for the JSON configuration file used by the application. It ensures that configurations are correctly formatted and validated before execution.

---

## Required Fields

| Field        | Type    | Description                                       | Constraints                  |
| ------------ | ------- |---------------------------------------------------|------------------------------|
| `n`          | Integer | Bit width of the binary strings to process.       | Must be a positive integer.  |
| `k`          | Integer | The number of active bits in each binary pattern. | Must be a positive integer.  |
| `block_size` | Integer | To be removed from public Implementation.         | # TODO remove from public    |

---

## Optional Fields

| Field         | Type    | Description                                                      | Constraints                                                                                     |
|---------------|---------|------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| `existential` | Boolean | Mode flag to toggle existential processing.                      | Defaults to `false` if omitted.                                                                 |
| `ranges`      | Array   | List of `[start, end]` pairs defining processing ranges.         | Each pair must be an array of two binary strings starting with `"0b"`. `start` must be ≤ `end`. |
| `prune_masks` | Array   | List of binary strings representing masks to prune certain data. | Each string must start with `"0b"`.                                                             |
| `find_masks`  | Array   | List of binary strings representing masks to find specific data. | Each string must start with `"0b"`.                                                             |
| `bit_flip`    | Boolean | Mode flag to toggle flipping bits and pruning once more.         | Defaults to 'false' if omitted. # TODO implement                                                |

---

## Validation Rules

* **Presence Checks**: The fields `n`, `k`, and `block_size` are mandatory.
* **Type Checks**:

    * `n`, `k`, and `block_size` must be integers greater than 0.
    * `existential` must be a boolean if provided.
    * `bit_flip` must be a boolean if provided.
    * `ranges` must be an array of arrays, each containing exactly two binary strings.
    * `prune_masks` and `find_masks` must be arrays of binary strings.
* **Format Checks**:

    * Binary strings must start with `"0b"` and contain only `0` or `1` characters.
    * In each range, the `start` value must not exceed the `end` value.

---

## Example Configuration

```json
{
  "n": 15,
  "k": 8,
  "block_size": 3,
  "existential": true,
  "prune_masks": [
    "0b000001001100111",
    "0b000010010101011"
  ],
  "find_masks": [
    "0b111000111000000",
    "0b111111000000000"
  ],
  "ranges": [
    [
      "0b000000000111111",
      "0b111111000000000"
    ]
  ]
}
```

---

## Common Errors and Solutions

* **Missing Required Fields**:

    * *Error*: `"Config must specify 'n' and 'k'."`
    * *Solution*: Ensure both `n` and `k` are present and correctly defined in the configuration.

* **Invalid Field Types**:

    * *Error*: `"'n' must be a positive integer."`
    * *Solution*: Verify that `n` is an integer greater than 0.

* **Incorrect Binary String Format**:

    * *Error*: `"Mask string must be in binary format starting with '0b'. Got: ..."`
    * *Solution*: Ensure all binary strings start with `"0b"` and contain only `0` or `1`.

* **Malformed Ranges**:

    * *Error*: `"\"ranges\" entries must be [start,end] arrays"`
    * *Solution*: Each range must be an array of two binary strings, e.g., `["0b0001", "0b0010"]`.

* **Start Greater Than End in Ranges**:

    * *Error*: `"Invalid range: start cannot be greater than end."`
    * *Solution*: Ensure that in each range, the `start` value is less than or equal to the `end` value.

---

## Notes

* All binary strings should be enclosed in double quotes and start with `"0b"`.
* Binary strings must include leading zeros which must agree with bit width.

---
