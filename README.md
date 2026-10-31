# consumer-viz-timeframes

A MMIF consumer that shows the `TimeFrame` annotations of one video or audio document. It writes one of these artifacts:

- `text`: a segmented bar for each view, with the share of each label
- `html`: one HTML page with a media player and a timeline for each view. Click the timeline to seek.

```
v_0 (http://apps.clams.ai/demo-language-id/v1)
|-E-E-E-E-E-S-S-S-S-S-S-S-S-X-S-S-S-S-S-S-S-S-S-S-E-E-E-E-E-E-E-E-E-E-|
S: es (50%)   E: en (43%)   X: no label (7%)
```

## Input requirements

| MMIF element | Use |
|---|---|
| `VideoDocument` or `AudioDocument` | Required. The document that has the `TimeFrame` annotations. |
| `TimeFrame` | Required. Times come from `start` and `end`, or from `targets`. |
| `TimeFrame` property `label` | Optional. A `TimeFrame` with no label is shown as `unlabeled`. |
| Document property `duration` | Optional. Without it, the timeline ends at the last `TimeFrame`, or you can use `--duration`. |

## Usage

The only dependency is `mmif-python`. See the options with:

```
python consume.py --help
```

Text mode, written to STDOUT:

```
python consume.py input.mmif
```

HTML mode:

```
python consume.py input.mmif --format html --document-location /path/to/video.mp4 -o page.html
```

Warnings and errors go to STDERR. The exit status is non-zero when no artifact is created.

## Media location

The `location` in a MMIF is where the file was when the apps ran, so it can be wrong on your computer. Text mode does not use the media file. HTML mode finds the reference for the player in this order:

1. the value of `--document-location`, which can be a full path or a URL
1. the `location` in the MMIF, when it is an `http` or `https` URL
1. the local path from the `location` in the MMIF, resolved with any installed document location plugins

When the media does not load, the page shows a button to choose the file on your computer. The file stays on your computer. This also works when you move the page to another computer.

The browser must be able to play the file. Many archive formats (for example, MPEG-2) do not play in a browser. The timeline still shows, but it can't control playback.

## License

Apache License 2.0. See [LICENSE](LICENSE).
