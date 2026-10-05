import type { Job } from "@/api/jobs";
import { EmptyState } from "@/components/common/empty-state";
import { Panel, PanelContent, PanelHeader } from "@/components/common/panel";
import { isActive } from "@/lib/job-status";
import { DownloadIcon, InboxIcon } from "lucide-react";
import { JobCard } from "./job-card";

type Props = {
  jobs: Job[];
  isLoading: boolean;
  onCancel: (jobId: string) => void;
  onDelete: (jobId: string) => void;
};

export function JobsPanel({ jobs, isLoading, onCancel, onDelete }: Props) {
  return (
    <Panel>
      <PanelHeader
        leadingIcon={<DownloadIcon size={15} strokeWidth={1.25} />}
        badge={
          jobs.length > 0 && (
            <span className="text-muted tnum text-[0.6875rem]">
              {jobs.length}
            </span>
          )
        }
      >
        Downloads
      </PanelHeader>
      {/* Grows with content up to a cap, so a single download does not sit in a
          half-empty panel. */}
      <PanelContent height="max-h-124 min-h-28" className="space-y-2">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <span className="text-muted font-mono text-sm">Loading...</span>
          </div>
        ) : jobs.length === 0 ? (
          <EmptyState icon={InboxIcon} title="No downloads yet" />
        ) : (
          <div className="flex flex-col gap-2">
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onCancel={isActive(job.status) ? onCancel : undefined}
                onDelete={!isActive(job.status) ? onDelete : undefined}
              />
            ))}
          </div>
        )}
      </PanelContent>
    </Panel>
  );
}
