import { listSubscriptions } from "@/api/subscriptions";
import { MetricRing } from "@/components/common/metric-ring";
import { useJobs } from "@/features/jobs/jobs-context";
import { isActive } from "@/lib/job-status";
import {
  AudioLinesIcon,
  CheckIcon,
  ListMusicIcon,
  ZapIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const ICON = "h-3.5 w-3.5";
const STROKE = 1.25;

/**
 * The metric row that opens the page.
 *
 * Everything here is derived from jobs already in memory, so the row costs one
 * extra request (the subscription count) rather than a new stats endpoint.
 */
export function StatsRow() {
  const { jobs } = useJobs();
  const [playlistCount, setPlaylistCount] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    listSubscriptions()
      .then((subs) => {
        if (!cancelled) setPlaylistCount(subs.length);
      })
      .catch(() => {
        if (!cancelled) setPlaylistCount(0);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const { tracks, successRate, activeCount, hasOutcome } = useMemo(() => {
    let success = 0;
    let failed = 0;

    for (const job of jobs) {
      success += job.download_stats?.success ?? 0;
      failed += job.download_stats?.failed ?? 0;
    }

    const attempted = success + failed;

    return {
      tracks: success,
      successRate:
        attempted === 0 ? 0 : Math.round((success / attempted) * 100),
      activeCount: jobs.filter((job) => isActive(job.status)).length,
      hasOutcome: attempted > 0,
    };
  }, [jobs]);

  return (
    <section
      aria-label="Library overview"
      className="mb-10 grid grid-cols-2 gap-y-8 sm:grid-cols-4 sm:gap-y-0"
    >
      <MetricRing
        label="Tracks"
        value={tracks}
        icon={<AudioLinesIcon className={ICON} strokeWidth={STROKE} />}
      />
      <MetricRing
        label="Success"
        value={hasOutcome ? `${successRate}` : "—"}
        icon={<CheckIcon className={ICON} strokeWidth={STROKE} />}
        progress={hasOutcome ? successRate / 100 : 0}
      />
      <MetricRing
        label="Active"
        value={activeCount}
        icon={<ZapIcon className={ICON} strokeWidth={STROKE} />}
      />
      <MetricRing
        label="Playlists"
        value={playlistCount ?? "—"}
        icon={<ListMusicIcon className={ICON} strokeWidth={STROKE} />}
      />
    </section>
  );
}
