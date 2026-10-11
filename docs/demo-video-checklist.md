# Demo Video Checklist

A checklist for recording a shareable OpsCommand demo video (60–90 seconds).
The content to show is defined in [`demo-script.md`](demo-script.md); this
document covers the production steps so the result is clean, private, and
ready to publish to GitHub, a portfolio site, LinkedIn, or an interview.

## Before recording

- [ ] Decide the target length (60s or 90s) and the audience.
- [ ] Re-read the matching version in `demo-script.md` and the talking points
      for that audience.
- [ ] Confirm you have a quiet environment and ~15 minutes of uninterrupted
      time.
- [ ] Charge / plug in your machine; close unrelated apps and notifications.
- [ ] Prepare a short intro and outro line (see `demo-script.md` → Final call
      to action).

## Application preparation

- [ ] Start the full stack: `cp .env.example .env && docker compose up --build`.
- [ ] Seed demo data: `docker compose exec backend python -m app.seed`.
- [ ] Confirm the `worker` service is running (`docker compose ps`).
- [ ] Verify the app loads at <http://localhost:5173> and you can sign in as
      `responder@acme-ops.io` / `Demo-Password-123!`.
- [ ] Run the full workflow once (dry run) to confirm every scene works before
      recording.
- [ ] Reset the demo state (re-seed) so the recording starts from a known
      state.

## Browser preparation

- [ ] Use a clean browser profile (no personal extensions, no saved passwords
      visible, no personal tabs).
- [ ] Disable or hide browser extensions that add overlays or toolbars.
- [ ] Set the zoom to 100% and the window to the recommended capture size.
- [ ] Clear the address bar of any sensitive history; use a fresh tab.
- [ ] Turn off "do not track" prompts, cookie banners, and update
      notifications.
- [ ] Confirm the connection indicator works (WebSocket to the API).

## Recording setup

- [ ] Choose a screen recorder (e.g. OBS Studio, or the OS built-in
      recorder).
- [ ] Set the capture region to the application window only (no desktop, no
      taskbar, no other windows).
- [ ] Set the resolution to match the recommended dimensions (e.g. 1440×900).
- [ ] Set the frame rate to 30 fps (smooth enough for UI, small enough to
      share).
- [ ] Do a 10-second test recording and review it before the real take.
- [ ] Keep a second tab/window ready for the real-time scene.

## Privacy and security review

- [ ] No real passwords, tokens, API keys, or secrets are visible.
- [ ] No personal email, name, or account details are shown.
- [ ] No other organizations' data is visible (the demo is org-scoped).
- [ ] The mock webhook does not display sensitive payloads.
- [ ] The address bar does not reveal a private hostname or internal URL.
- [ ] Any on-screen text (timeline notes, action items) is generic and safe.
- [ ] Re-check the final video frame-by-frame for anything sensitive.

## Required scenes

Record at least these (in order), matching `demo-script.md`:

- [ ] Sign in (connection indicator turns green).
- [ ] Dashboard with the active SEV2 incident.
- [ ] Incident command view (status, roles, timeline, action items, playbooks).
- [ ] Status transition with the timeline updating.
- [ ] Role assignment (commander + operations).
- [ ] Playbook run with live per-step progress.
- [ ] Real-time proof (a second tab shows the change without a reload).
- [ ] Resolve + export the Markdown report.
- [ ] (Optional) Authorization beat (viewer is read-only).

## Audio checklist

- [ ] Microphone is working and at a comfortable level.
- [ ] No background noise (fans, keyboard, notifications).
- [ ] Speak clearly and at a steady pace; pause between beats.
- [ ] Record a 5-second audio test and listen it back.
- [ ] If narrating over the recording, keep the script in front of you.

## Visual quality checklist

- [ ] Text is legible at the capture resolution.
- [ ] No flicker, tearing, or dropped frames.
- [ ] Colors and contrast are consistent (no dark-mode flash).
- [ ] The cursor is visible and moves deliberately.
- [ ] No accidental clicks, typos, or dead ends on screen.
- [ ] Transitions between scenes are clean (no long pauses).

## Export settings

- [ ] Export as **MP4 (H.264)** for broad compatibility.
- [ ] Resolution: 1440×900 or 1920×1080.
- [ ] Frame rate: 30 fps.
- [ ] Bitrate: enough for crisp text (e.g. 8–12 Mbps for 1080p).
- [ ] Keep the file under ~100 MB for easy sharing.
- [ ] Name the file descriptively (e.g. `opscommand-demo-90s.mp4`).

## Final review

- [ ] Watch the full video once at normal speed.
- [ ] Confirm the story is clear to a non-technical viewer.
- [ ] Confirm no sensitive information is visible or audible.
- [ ] Confirm the length is within the target (60–90s).
- [ ] Confirm the intro states what the project is and why it matters.
- [ ] Confirm the outro points to the repository / next step.
- [ ] Get a second pair of eyes if possible.

## Publishing checklist

- [ ] Add a concise title and description (what it is, what it shows, link to
      the repo).
- [ ] Add the repository link and (if available) the live/portfolio link.
- [ ] Include the key talking points in the description for SEO / scanning.
- [ ] Add a thumbnail that shows the dashboard or command view.
- [ ] Tag appropriately (incident response, full-stack, FastAPI, React, etc.).
- [ ] Verify the video plays on the target platform (GitHub, portfolio,
      LinkedIn).
- [ ] Keep a local copy of the master file.
