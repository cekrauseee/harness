---
description: >-
  Connaissances persistantes et coordination du travail entre agents, tâches et
  dépôts.
metaDescription: >-
  Continuity conserve les décisions importantes, les découvertes utiles et le
  travail inachevé pour les rendre accessibles d'une tâche à l'autre. Les
  connaissances résident dans des fichiers Markdown locaux, en dehors des
  dépôts.
summary: >-
  Continuity conserve les décisions importantes, les découvertes utiles et le
  travail inachevé. J'ai créé le projet pour que ce contexte reste disponible
  lorsque le travail passe à une nouvelle conversation ou à un autre agent.
  Quatre skills indépendants guident la configuration des environnements, la
  récupération du contexte, la gestion des connaissances et la coordination des
  modifications partagées.
highlights:
  - connaissances dans des fichiers Markdown locaux, en dehors des dépôts
  - quatre skills indépendants
  - récupération du contexte quand la tâche le requiert
  - réservations de fichiers et coordination atomique
---

Continuity conserve les décisions importantes, les découvertes utiles et le travail inachevé. J'ai créé le projet pour que ce contexte reste disponible lorsque le travail passe à une nouvelle conversation ou à un autre agent.

Quatre skills indépendants guident la configuration des environnements, la récupération du contexte, la gestion des connaissances et la coordination des modifications partagées.

## Partager les connaissances entre projets

Les connaissances résident dans des fichiers Markdown locaux, en dehors des dépôts. Des projets associés peuvent appartenir au même environnement et partager des notes et des contributions, tout en conservant l'identité propre à chaque répertoire de travail.

Cette appartenance est explicite. Une contribution peut couvrir des fichiers de plusieurs dépôts tout en conservant la trace du projet dans lequel elle a commencé. Les Git worktrees partagent l'environnement de leur dépôt, mais restent des espaces de travail distincts.

## Récupérer le contexte quand la tâche le requiert

Les skills invitent les agents à commencer par la demande et les informations déjà disponibles. Le savoir enregistré est consulté lorsqu'une décision antérieure ou un fait manquant peut influencer la manière d'aborder la tâche.

Les notes conservent leur périmètre, leurs sources et leurs incertitudes. Les décisions confirmées restent distinctes des hypothèses, et les informations déjà suffisamment documentées dans un projet peuvent rester à leur source d'origine.

## Coordonner les modifications et le travail inachevé

Un utilitaire Python vérifie les réservations de fichiers qui se chevauchent et protège les mises à jour des connaissances pour éviter qu'elles n'écrasent un contenu modifié depuis la dernière lecture.

Lorsqu'une tâche doit être reprise plus tard, sa contribution conserve un résumé de l'état actuel et des prochaines étapes. Une fois le travail terminé, les connaissances pertinentes sont consolidées, puis la contribution et ses réservations sont supprimées en une seule opération atomique.

Les réservations coordonnent les agents qui suivent la même procédure. Elles n'empêchent pas les modifications effectuées avec d'autres outils, une limite importante de cette approche.
