# Battery Vision HMI

Industrial demo UI for the segmentation, tracking, volume, and simulated conveyor-safety workflow.

## Run locally

The UI expects rendered inference assets at `/final-product/`. During development, Vite proxies that path to the artifact server on port `8765`.

```bash
# Terminal 1: expose the AWS-rendered result (or serve a local result directory)
ssh -i hackathon-training-1.pem -N \
  -L 8765:127.0.0.1:8765 ubuntu@18.219.97.222

# Terminal 2
cd dashboard
npm ci
npm run dev
```

Open the Vite URL under `/dashboard/`. The HMI plays `final-product.mp4`, reads `summary.json`, and displays the live lot count, volume estimate, confirmed tracks, and mask confidence.

## Simulated safety computer

This is a software-only PLC simulation. The operator can inject a warning, stop the conveyor, continue it, or reset the lot. With auto-guard enabled, the demo transitions from `RUNNING` to `WARNING` and then `STOPPED`, pausing video playback and opening the simulated motor relay. It does not control real hardware.

## Vision pipeline shown in the demo

- YOLO26 instance segmentation fine-tuned on full-tray battery masks at 960 px.
- Full visible tray ROI to reject detections on the surrounding machinery.
- Two-stage high/low-confidence global association inspired by ByteTrack.
- Constant-velocity Kalman prediction with IoU, scale, direction, and mask-appearance costs.
- Confirmed-track hysteresis at the counting gate to reduce duplicate counts.
- Approximate 5900 x 1500 mm tray homography and catalog-constrained volume estimates.

The masks, physical calibration, and volume estimates are provisional demo outputs until human-reviewed annotations and camera calibration are complete.

## Checks

```bash
npm run lint
npm run build
```
