import React, { useRef, useEffect } from 'react';

const COLORS = {
  SKIN: '#fcdcc6',
  SKIN_SHADOW: '#eac3a5',
  HAND: '#f8c8a8',
  HAND_STROKE: '#d4a383',
  HAIR: '#1a1a1a',
  JACKET: '#3f51b5',
  SLEEVE: '#5c6bc0',
  LAPEL: '#1a237e',
  SHIRT: '#ff9800',
  PANTS: '#6d4c41',
  SHOE: '#bc5a3a',
  NOSE: '#f89a94',
  EYE: '#2e7d32',
  SKELETON: '#00e5ff'
};

const FINGER_LANDMARKS = {
  thumb: [0, 1, 2, 3, 4],
  index: [0, 5, 6, 7, 8],
  middle: [0, 9, 10, 11, 12],
  ring: [0, 13, 14, 15, 16],
  pinky: [0, 17, 18, 19, 20]
};

const SKELETON_CONNECTIONS = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24], [23, 25], [25, 27],
  [24, 26], [26, 28]
];

const AvatarCanvas = ({ points, caption }) => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    if (!points || points.length < 75) return;

    // Scale points to canvas size (assuming input is 0-1)
    const pts = points.map(p => ({
      x: p[0] * canvas.width,
      y: p[1] * canvas.height
    }));

    const getPt = (idx) => pts[idx] && pts[idx].x > 1 && pts[idx].y > 1 ? pts[idx] : null;

    // Helper to draw polygons
    const drawPoly = (indices, color) => {
      ctx.fillStyle = color;
      ctx.beginPath();
      indices.forEach((idx, i) => {
        const p = typeof idx === 'number' ? getPt(idx) : idx;
        if (p) {
          if (i === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        }
      });
      ctx.closePath();
      ctx.fill();
    };

    const nose = getPt(0);
    const p11 = getPt(11), p12 = getPt(12);
    const p23 = getPt(23), p24 = getPt(24);
    const p27 = getPt(27), p28 = getPt(28);

    const shoulderDist = p11 && p12 ? Math.hypot(p11.x - p12.x, p11.y - p12.y) : 60;
    const headR = shoulderDist * 0.45;

    // 0. Background Gradient
    const bgGrad = ctx.createRadialGradient(canvas.width/2, canvas.height/2, 50, canvas.width/2, canvas.height/2, canvas.width/2);
    bgGrad.addColorStop(0, '#1a1c2c');
    bgGrad.addColorStop(1, '#0c0d16');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Ground Shadow
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.beginPath();
    ctx.ellipse(canvas.width/2, canvas.height - 40, 100, 20, 0, 0, Math.PI * 2);
    ctx.fill();

    // 1. Hair Background (Layered)
    if (nose) {
      // Rim Light
      ctx.shadowBlur = 15;
      ctx.shadowColor = 'rgba(255,255,255,0.1)';
      
      const hairGrad = ctx.createLinearGradient(nose.x, nose.y - headR * 1.5, nose.x, nose.y + headR);
      hairGrad.addColorStop(0, COLORS.HAIR);
      hairGrad.addColorStop(1, '#000');
      
      ctx.fillStyle = hairGrad;
      ctx.beginPath();
      ctx.ellipse(nose.x, nose.y - headR * 0.2, headR * 1.25, headR * 1.35, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0; // Reset
    }

    // 2. Neck
    if (nose && p11 && p12) {
      const midS = { x: (p11.x + p12.x) / 2, y: (p11.y + p12.y) / 2 };
      ctx.fillStyle = COLORS.SKIN;
      ctx.beginPath();
      ctx.ellipse(nose.x, (nose.y + midS.y) / 2, headR * 0.25, Math.abs(nose.y - midS.y) * 0.35, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    // 3. Torso & Clothes
    if (p11 && p12 && p23 && p24) {
      const midS = { x: (p11.x + p12.x) / 2, y: (p11.y + p12.y) / 2 };
      const neckBottom = { x: midS.x, y: midS.y + shoulderDist * 0.1 };
      const hipMid = { x: (p23.x + p24.x) / 2, y: (p23.y + p24.y) / 2 };
      const pW = shoulderDist * 0.2;

      // Shirt (V-neck)
      drawPoly([
        { x: neckBottom.x - pW, y: neckBottom.y },
        { x: neckBottom.x + pW, y: neckBottom.y },
        { x: hipMid.x + pW * 1.2, y: hipMid.y },
        { x: hipMid.x - pW * 1.2, y: hipMid.y }
      ], COLORS.SHIRT);

      // Jacket (Structured)
      drawPoly([p11, { x: neckBottom.x - pW, y: neckBottom.y }, { x: hipMid.x - pW * 1.1, y: hipMid.y }, { x: p23.x - 15, y: p23.y }], COLORS.JACKET);
      drawPoly([p12, { x: neckBottom.x + pW, y: neckBottom.y }, { x: hipMid.x + pW * 1.1, y: hipMid.y }, { x: p24.x + 15, y: p24.y }], COLORS.JACKET);

      // Lapels
      const lW = shoulderDist * 0.3, lH = shoulderDist * 0.6;
      drawPoly([ { x: neckBottom.x - pW, y: neckBottom.y }, { x: neckBottom.x - pW - lW, y: neckBottom.y + lH }, { x: neckBottom.x - pW, y: neckBottom.y + lH * 0.4 } ], COLORS.LAPEL);
      drawPoly([ { x: neckBottom.x + pW, y: neckBottom.y }, { x: neckBottom.x + pW + lW, y: neckBottom.y + lH }, { x: neckBottom.x + pW, y: neckBottom.y + lH * 0.4 } ], COLORS.LAPEL);

      // Pants (Full Legs)
      const drawLeg = (h, k, a) => {
        if (!h || !k || !a) return;
        ctx.strokeStyle = COLORS.PANTS; ctx.lineWidth = 20; ctx.beginPath(); ctx.moveTo(h.x, h.y); ctx.lineTo(k.x, k.y); ctx.stroke();
        ctx.lineWidth = 16; ctx.beginPath(); ctx.moveTo(k.x, k.y); ctx.lineTo(a.x, a.y); ctx.stroke();
        // Shoe
        ctx.fillStyle = COLORS.SHOE; ctx.beginPath(); ctx.ellipse(a.x, a.y + 5, 12, 6, 0, 0, Math.PI * 2); ctx.fill();
      };
      drawLeg(getPt(23), getPt(25), getPt(27));
      drawLeg(getPt(24), getPt(26), getPt(28));
    }

    // 4. Limbs
    ctx.lineCap = 'round';
    SKELETON_CONNECTIONS.forEach(([i1, i2]) => {
      const pt1 = getPt(i1), pt2 = getPt(i2);
      if (pt1 && pt2) {
        // Outer Clothing/Arm
        ctx.strokeStyle = COLORS.JACKET;
        ctx.lineWidth = 18; // Thicker limbs
        ctx.beginPath();
        ctx.moveTo(pt1.x, pt1.y);
        ctx.lineTo(pt2.x, pt2.y);
        ctx.stroke();
        
        // Inner detail/Shadow
        ctx.strokeStyle = 'rgba(0,0,0,0.05)';
        ctx.lineWidth = 8;
        ctx.stroke();
      }
    });

    // Shoulder Sleeves
    if (p11) {
        ctx.fillStyle = COLORS.SLEEVE;
        ctx.beginPath(); ctx.ellipse(p11.x, p11.y + 10, 15, 20, 0, 0, Math.PI * 2); ctx.fill();
    }
    if (p12) {
        ctx.fillStyle = COLORS.SLEEVE;
        ctx.beginPath(); ctx.ellipse(p12.x, p12.y + 10, 15, 20, 0, 0, Math.PI * 2); ctx.fill();
    }

    // 5. Head Face
    if (nose) {
      // Face Shadow from Hair
      ctx.fillStyle = 'rgba(0,0,0,0.1)';
      ctx.beginPath();
      ctx.ellipse(nose.x, nose.y - headR * 0.1, headR * 1.1, headR * 1.2, 0, 0, Math.PI * 2);
      ctx.fill();

      // Face Base
      ctx.fillStyle = COLORS.SKIN;
      ctx.beginPath();
      ctx.ellipse(nose.x, nose.y, headR * 1.05, headR * 1.15, 0, 0, Math.PI * 2);
      ctx.fill();

      // Eyebrows
      ctx.strokeStyle = COLORS.HAIR;
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.beginPath(); 
      ctx.arc(nose.x - headR * 0.45, nose.y - headR * 0.35, headR * 0.15, Math.PI * 1.1, Math.PI * 1.5); 
      ctx.stroke();
      ctx.beginPath(); 
      ctx.arc(nose.x + headR * 0.45, nose.y - headR * 0.35, headR * 0.15, Math.PI * 1.5, Math.PI * 1.9); 
      ctx.stroke();

      // Eyes (Detailed)
      const drawEye = (x, y) => {
        // Sclera
        ctx.fillStyle = 'white';
        ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fill();
        // Iris
        ctx.fillStyle = COLORS.EYE;
        ctx.beginPath(); ctx.arc(x, y, 3.5, 0, Math.PI * 2); ctx.fill();
        // Pupil
        ctx.fillStyle = 'black';
        ctx.beginPath(); ctx.arc(x, y, 1.5, 0, Math.PI * 2); ctx.fill();
        // Highlight
        ctx.fillStyle = 'white';
        ctx.beginPath(); ctx.arc(x - 1.5, y - 1.5, 1, 0, Math.PI * 2); ctx.fill();
      };
      drawEye(nose.x - headR * 0.45, nose.y - headR * 0.1);
      drawEye(nose.x + headR * 0.45, nose.y - headR * 0.1);

      // Nose (Shaded)
      const noseGrad = ctx.createRadialGradient(nose.x, nose.y + headR * 0.15, 1, nose.x, nose.y + headR * 0.15, 6);
      noseGrad.addColorStop(0, COLORS.NOSE);
      noseGrad.addColorStop(1, COLORS.SKIN);
      ctx.fillStyle = noseGrad;
      ctx.beginPath(); ctx.ellipse(nose.x, nose.y + headR * 0.15, 4, 7, 0, 0, Math.PI * 2); ctx.fill();

      // Mouth (Lips)
      ctx.fillStyle = '#bc5a3a';
      ctx.beginPath();
      ctx.ellipse(nose.x, nose.y + headR * 0.55, 10, 3, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#4e342e'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(nose.x - 10, nose.y + headR * 0.55); ctx.lineTo(nose.x + 10, nose.y + headR * 0.55); ctx.stroke();

      // --- Hair Swoop (Black & Sharp) ---
      ctx.fillStyle = COLORS.HAIR;
      ctx.beginPath();
      ctx.moveTo(nose.x - headR * 1.15, nose.y - headR * 0.4);
      ctx.lineTo(nose.x - headR * 0.95, nose.y - headR * 1.05);
      ctx.lineTo(nose.x - headR * 0.4, nose.y - headR * 1.25);
      ctx.lineTo(nose.x + headR * 0.4, nose.y - headR * 1.3);
      ctx.lineTo(nose.x + headR * 1.05, nose.y - headR * 1.0);
      ctx.lineTo(nose.x + headR * 1.15, nose.y - headR * 0.3);
      ctx.lineTo(nose.x + headR * 0.4, nose.y - headR * 0.5);
      ctx.lineTo(nose.x - headR * 0.4, nose.y - headR * 0.5);
      ctx.closePath();
      ctx.fill();

      // Hair Highlights (Detail)
      ctx.strokeStyle = 'rgba(255,255,255,0.08)';
      ctx.lineWidth = 1.5;
      for (let i = 0; i < 15; i++) {
        ctx.beginPath();
        ctx.moveTo(nose.x - headR + (i * 8), nose.y - headR * 0.9);
        ctx.lineTo(nose.x - headR + (i * 8) + 8, nose.y - headR * 1.2);
        ctx.stroke();
      }
    }

    // 6. Hands and Fingers
    const wristL = getPt(15), wristR = getPt(16);
    
    // Draw Palms (Larger)
    ctx.strokeStyle = COLORS.HAND_STROKE;
    ctx.lineWidth = 1.5;
    if (wristL) {
      ctx.fillStyle = COLORS.HAND;
      ctx.beginPath();
      ctx.ellipse(wristL.x, wristL.y, 12, 10, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
    if (wristR) {
      ctx.fillStyle = COLORS.HAND;
      ctx.beginPath();
      ctx.ellipse(wristR.x, wristR.y, 12, 10, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }

    // Draw Detailed Fingers (Thicker)
    const drawHand = (startIdx) => {
      Object.values(FINGER_LANDMARKS).forEach(ids => {
        ctx.strokeStyle = COLORS.HAND_STROKE;
        ctx.lineWidth = 5; // Thicker fingers
        ctx.lineCap = 'round';
        ctx.beginPath();
        let first = true;
        ids.forEach((id) => {
          const pt = getPt(startIdx + id);
          if (pt) {
            if (first) {
              ctx.moveTo(pt.x, pt.y);
              first = false;
            } else {
              ctx.lineTo(pt.x, pt.y);
            }
          }
        });
        ctx.stroke();

        // Optional: Inner skin color for fingers to make them look like solid tubes
        ctx.strokeStyle = COLORS.HAND;
        ctx.lineWidth = 3;
        ctx.stroke();
      });
    };

    drawHand(33); // Left Hand
    drawHand(54); // Right Hand

    // 7. Caption
    if (caption) {
      ctx.fillStyle = '#ff69b4';
      ctx.font = 'bold 24px Inter';
      ctx.textAlign = 'right';
      ctx.fillText(caption.toUpperCase(), canvas.width - 20, canvas.height - 30);
    }

  }, [points, caption]);

  return (
    <canvas 
      ref={canvasRef} 
      width={640} 
      height={480} 
      className="avatar-canvas"
    />
  );
};

export default AvatarCanvas;
