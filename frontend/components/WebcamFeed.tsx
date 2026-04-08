"use client";

import Webcam from "react-webcam";

interface Props {
  webcamRef: React.RefObject<Webcam | null>;
}

export function WebcamFeed({ webcamRef }: Props) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-panel shadow-glow">
      <Webcam
        audio={false}
        ref={webcamRef}
        mirrored
        screenshotFormat="image/jpeg"
        screenshotQuality={0.9}
        videoConstraints={{ width: 640, height: 480, facingMode: "user" }}
        className="h-auto w-full"
      />
    </div>
  );
}
