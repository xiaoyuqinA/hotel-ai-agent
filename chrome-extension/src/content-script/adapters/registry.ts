import type { OTAAdapter } from "./types.js";
import { CtripAdapter } from "./ctrip/index.js";
import { FliggyAdapter } from "./fliggy/index.js";
import { BookingAdapter } from "./booking/index.js";
import { AgodaAdapter } from "./agoda/index.js";
import { GenericAdapter } from "./generic/index.js";

const specialAdapters: OTAAdapter[] = [
  new CtripAdapter(),
  new FliggyAdapter(),
  new BookingAdapter(),
  new AgodaAdapter(),
];

const genericAdapter = new GenericAdapter();

export async function detectAdapter(): Promise<OTAAdapter | null> {
  for (const adapter of specialAdapters) {
    if (await adapter.matches()) return adapter;
  }
  // 无 OTA 平台匹配时使用通用 adapter
  return genericAdapter;
}
