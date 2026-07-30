import type { OTAAdapter } from "./types.js";
import { CtripAdapter } from "./ctrip/index.js";
import { FliggyAdapter } from "./fliggy/index.js";
import { BookingAdapter } from "./booking/index.js";
import { AgodaAdapter } from "./agoda/index.js";

const adapters: OTAAdapter[] = [
  new CtripAdapter(),
  new FliggyAdapter(),
  new BookingAdapter(),
  new AgodaAdapter(),
];

export async function detectAdapter(): Promise<OTAAdapter | null> {
  for (const adapter of adapters) {
    if (await adapter.matches()) return adapter;
  }
  return null;
}
