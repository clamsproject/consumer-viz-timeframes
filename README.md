# consumer-viz-timeframes

A MMIF consumer that shows the `TimeFrame` annotations of one video or audio document. It writes one of these artifacts:

- `text`: rows of characters for each view, with a legend. A character is 10 s, a group of six characters is one minute, and a row is 10 minutes.
- `html`: one HTML page with a media player and a timeline for each view. Click the timeline to seek.

```
Duration 2:00. A row is 10 minutes, a group 1 minute, and a character 10 s.
A character shows the label with the most time in it, in lower case when
that label covers less than half of it.

v_0 (http://apps.clams.ai/demo-language-id/v1)
0:00 |EESSsS SSSEEE|
S: es (50%, 2 TimeFrames)   E: en (43%, 2 TimeFrames)   .: no TimeFrame (7%)
```

In text mode, `.` marks 10 s with no `TimeFrame`. In each view, the ten labels with the most time get a letter of their own, and the other labels share `*`.

## Input requirements

| MMIF element | Use |
|---|---|
| `VideoDocument` or `AudioDocument` | Required. The document that has the `TimeFrame` annotations. |
| `TimeFrame` | Required. Times come from `start` and `end`, or from `targets`. |
| `TimeFrame` property `label` | Optional. A `TimeFrame` with no label is shown as `unlabeled`. |
| Document property `duration` | Optional. Without it, the timeline ends at the last `TimeFrame`, or you can use `--duration`. |

## Usage

Install the `viz-timeframes` command. The only dependency is `mmif-python`.

```
pip install git+https://github.com/clamsproject/consumer-viz-timeframes
```

Text mode, written to STDOUT:

```
viz-timeframes input.mmif
```

HTML mode, chosen by the `.html` extension of the output path (`--format` sets the mode explicitly):

```
viz-timeframes input.mmif -o page.html
```

See `viz-timeframes --help` for the other options. Warnings and errors go to STDERR. The exit status is non-zero when no artifact is created. In a clone of the repository, `python consume.py` runs the same command line.

## Development

Install the test dependencies with `pip install -e '.[test]'` and run `pytest` from the repository root.

## Media location

The `location` in a MMIF is where the file was when the apps ran, so it can be wrong on your computer. Text mode does not use the media file. HTML mode finds the reference for the player in this order:

1. the value of `--document-location`, which can be a full path or a URL
1. the `location` in the MMIF, when it is an `http` or `https` URL
1. the local path from the `location` in the MMIF, resolved with any installed document location plugins

When the media does not load, the page shows a button to choose the file on your computer. The file stays on your computer. This also works when you move the page to another computer.

The browser must be able to play the file. Many archive formats (for example, MPEG-2) do not play in a browser. The timeline still shows, but it can't control playback.

## License

Apache License 2.0. See [LICENSE](LICENSE).
