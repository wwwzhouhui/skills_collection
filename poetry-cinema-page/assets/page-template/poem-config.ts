export type PoetrySection = {
  id: string;
  image: string;
  index: string;
  original: string;
  literal: string;
  analysis: string;
};

export const poem = {
  title: '{{TITLE}}',
  author: '{{AUTHOR}}',
  era: '{{ERA}}',
  kicker: '{{KICKER}}',
  definingLine: '{{DEFINING_LINE}}',
  intro: '{{INTRO}}',
  heroImage: '/generated/{{SLUG}}/hero.jpg',
  audioSrc: '',
  sections: [] as PoetrySection[],
};
