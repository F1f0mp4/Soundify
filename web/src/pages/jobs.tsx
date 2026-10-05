import { UrlInput } from "@/components/common/url-input";
import { JobsPanel } from "@/features/jobs/jobs-panel";
import { useJobs } from "@/features/jobs/jobs-context";
import { LogsPanel } from "@/features/logs/logs-panel";
import { StatsRow } from "@/features/stats/stats-row";
import { isValidUrl } from "@/lib/url";
import { Button, InputGroup, NumberField } from "@heroui/react";
import { ArrowRightIcon, HashIcon } from "lucide-react";
import { memo, useState } from "react";

const DEFAULT_MAX_ITEMS = 100;

interface DownloadFormProps {
  onDownload: (url: string, maxItems: number) => Promise<void>;
}

/**
 * The single most important control on the page, so it gets its own floating
 * surface and sits directly under the metrics rather than in a toolbar.
 */
const DownloadForm = memo(function DownloadForm({
  onDownload,
}: DownloadFormProps) {
  const [url, setUrl] = useState("");
  const [maxItems, setMaxItems] = useState(DEFAULT_MAX_ITEMS);

  const canDownload = isValidUrl(url);

  const handleDownload = async () => {
    if (canDownload) {
      await onDownload(url, maxItems);
      setUrl("");
    }
  };

  return (
    <section className="glass mb-8 rounded-[1.75rem] p-2.5">
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center">
        <div className="min-w-0 flex-1">
          <UrlInput
            value={url}
            onChange={setUrl}
            placeholder="Paste a YouTube Music or Spotify link"
          />
        </div>

        <div className="flex items-center gap-2.5">
          <NumberField
            className="w-24 shrink-0"
            aria-label="Max number of tracks to download"
            value={maxItems}
            onChange={(value) => {
              if (!Number.isNaN(value) && value >= 1) setMaxItems(value);
            }}
            minValue={1}
            maxValue={10000}
          >
            <InputGroup className="rounded-full border-0 bg-transparent">
              <InputGroup.Prefix>
                <HashIcon
                  className="text-muted h-3.5 w-3.5"
                  strokeWidth={1.25}
                />
              </InputGroup.Prefix>
              <InputGroup.Input
                placeholder="Max"
                className="tnum w-full min-w-0 bg-transparent"
              />
            </InputGroup>
          </NumberField>

          <Button
            variant="primary"
            className="h-11 shrink-0 rounded-full px-6 text-xs tracking-[0.16em] uppercase max-sm:flex-1"
            onPress={handleDownload}
            isDisabled={!canDownload}
          >
            Download
            <ArrowRightIcon className="h-4 w-4" strokeWidth={1.5} />
          </Button>
        </div>
      </div>
    </section>
  );
});

export function JobsPage() {
  const { jobs, isLoading, startJob, cancelJob, deleteJob } = useJobs();

  const handleDeleteJob = async (jobId: string) => {
    await deleteJob(jobId);
  };

  return (
    <>
      <StatsRow />

      <DownloadForm onDownload={startJob} />

      <section className="flex flex-col gap-6">
        <JobsPanel
          jobs={jobs}
          isLoading={isLoading}
          onCancel={cancelJob}
          onDelete={handleDeleteJob}
        />
        <LogsPanel jobs={jobs} />
      </section>
    </>
  );
}
