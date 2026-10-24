import { create } from "zustand";

interface DemoStore {
  selectedSubjectId: string;
  selectSubject: (subjectId: string) => void;
}

export const useDemoStore = create<DemoStore>((set) => ({
  selectedSubjectId: "corr-5",
  selectSubject: (selectedSubjectId) => set({ selectedSubjectId })
}));
