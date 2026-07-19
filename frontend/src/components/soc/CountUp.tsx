import { useEffect, useRef, useState } from "react";

export function CountUp({ to, duration = 1500, suffix = "", prefix = "" }: { to: number; duration?: number; suffix?: string; prefix?: string }) {
  const [v, setV] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const started = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !started.current) {
        started.current = true;
        const start = performance.now();
        const step = (now: number) => {
          const k = Math.min(1, (now - start) / duration);
          setV(to * (1 - Math.pow(1 - k, 3)));
          if (k < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      }
    }, { threshold: 0.3 });
    io.observe(el);
    return () => io.disconnect();
  }, [to, duration]);

  const formatted = v >= 1000 ? Math.round(v).toLocaleString() : v < 10 ? v.toFixed(1) : Math.round(v).toString();
  return <span ref={ref} className="text-mono">{prefix}{formatted}{suffix}</span>;
}
