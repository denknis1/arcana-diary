// A tarot card face (design system: TarotCard): the whole printed card in a gold frame, the name as text next to
// it; a reversed card turns only the picture.
import { fill, t } from '../../i18n';
import { cardById, cardImage, cardSrcset } from '../../lib/deck';
import type { Lang } from '../../lib/types';

interface ArtProps {
  cardId: string;
  name: string;
  reversed: boolean;
  lang: Lang;
  sizes?: string;
}

export function CardArt({ cardId, name, reversed, lang, sizes = '(min-width: 900px) 180px, 150px' }: ArtProps) {
  const card = cardById(cardId);
  if (!card) return null;
  const d = t(lang);
  return (
    <div class="card-frame__art">
      <img
        src={cardImage(card, 350)}
        srcset={cardSrcset(card)}
        sizes={sizes}
        width={350}
        height={600}
        alt={fill(reversed ? d.cardAltReversed : d.cardAlt, { name })}
        class={reversed ? 'is-reversed' : undefined}
      />
    </div>
  );
}

export function CardName({ cardId, name }: { cardId: string; name: string }) {
  const card = cardById(cardId);
  return (
    <span class="card-frame__name">
      {card ? <b>{card.numeral}</b> : null} {name}
    </span>
  );
}

export function CardFace(props: ArtProps) {
  return (
    <figure class="card-frame">
      <CardArt {...props} />
      <figcaption>
        <CardName cardId={props.cardId} name={props.name} />
      </figcaption>
    </figure>
  );
}
