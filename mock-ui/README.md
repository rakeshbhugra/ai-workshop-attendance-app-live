# Schoolnet Workshop Hub mock

Open `index.html` in Chrome. No installation, server, or backend is required.

The prototype follows the reference layout: navigation sidebar, workshop list, and a details panel with Overview, Students, Sessions, and Attendance tabs. It uses the authentic Schoolnet logo and locally downloaded Lato and Poppins fonts. Student avatars are initials, not real student photographs.

## Try the prototype

- Select a workshop and explore its tabs.
- Mark attendance individually or mark every enrolled student Present.
- Enter check-in and check-out times; invalid ordering is rejected.
- Add students or archive them. Recorded historical attendance is preserved.
- Open a calendar session to jump to attendance.
- Filter reports by workshop and download the matching CSV.
- Reset demo data from the sidebar.

All names and records are fictional. Edits stay in this browser's local storage. This prototype has no authentication, backend, or production access controls. Its sample clock and schedule are October 2026. Future sessions are included in Unmarked totals and excluded from attendance-rate denominators.

## Mock JSON data

`mock-data.json` contains students, workshops, sessions, and attendance records keyed by `sessionId:studentId`. `mock-data.js` is a generated copy loaded by the UI so it also works when opened directly as a local file. After editing the JSON, run:

```sh
python3 mock-ui/sync-data.py
```

Reset demo data in the UI to replace any locally saved edits with the revised sample dataset.

## Styling

Brand values: green `#0AA34F`, blue `#007CDC`, pale surface `#F9FAFC`. Small-text actions use accessible darker variants `#07833F` and `#0068B8`. Lato is used for body text and headings; Poppins is used for buttons and metric numbers. Application tables, forms, and status badges are adaptations of the supplied Schoolnet guide.
