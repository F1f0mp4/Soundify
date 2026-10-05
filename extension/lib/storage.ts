import { storage } from "wxt/utils/storage";

export const soundifyUrl = storage.defineItem<string>("sync:soundifyUrl");
export const soundifyUrlDraft = storage.defineItem<string>(
  "session:soundifyUrlDraft",
);
