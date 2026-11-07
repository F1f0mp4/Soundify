import { InputGroup, NumberField } from "@heroui/react";
import { HashIcon } from "lucide-react";

type TrackLimitFieldProps = {
  /** The limit the user typed, or undefined for "download everything". */
  value: number | undefined;
  onChange: (value: number | undefined) => void;
  isDisabled?: boolean;
  "aria-label": string;
};

/**
 * Optional cap on how many tracks to take. Empty by default: a playlist is
 * only cut short when the user asks for it, never by a pre-filled number.
 */
export function TrackLimitField({
  value,
  onChange,
  isDisabled,
  "aria-label": ariaLabel,
}: TrackLimitFieldProps) {
  return (
    <NumberField
      className="w-24 shrink-0"
      aria-label={ariaLabel}
      // NumberField renders NaN as an empty input.
      value={value ?? Number.NaN}
      onChange={(next) => {
        onChange(Number.isNaN(next) || next < 1 ? undefined : next);
      }}
      minValue={1}
      maxValue={10000}
      isDisabled={isDisabled}
    >
      <InputGroup className="rounded-full border-0 bg-transparent">
        <InputGroup.Prefix>
          <HashIcon className="text-muted h-3.5 w-3.5" strokeWidth={1.25} />
        </InputGroup.Prefix>
        <InputGroup.Input
          placeholder="All"
          className="tnum w-full min-w-0 bg-transparent"
        />
      </InputGroup>
    </NumberField>
  );
}
