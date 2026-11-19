import type { DeptKey, Mode, PublicData } from '../types';
import type { SetupItem } from '../sample';

export type TabProps = {
  data: PublicData;
  mode: Mode;
  dept: DeptKey;
  setup: SetupItem[];
  toggleSetup: (key: string) => void;
};
