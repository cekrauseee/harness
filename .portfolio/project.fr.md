---
description: >-
  Contexte externe par projet et procédures de développement ciblées pour les agents.
metaDescription: >-
  Harness conserve les connaissances utiles et le contexte de reprise dans des fichiers Markdown locaux, hors du dépôt. Quinze skills indépendants couvrent la planification, la réalisation, la revue et les opérations Git.
summary: >-
  Harness fournit à chaque projet un environnement externe partagé par ses worktrees Git. Quinze skills indépendants couvrent le contexte, la planification modulaire, les transmissions, la coordination des agents et les procédures de développement. Les agents lisent uniquement les éléments nécessaires à leur tâche.
highlights:
  - un environnement par projet et ses worktrees
  - quinze skills indépendants
  - contexte conservé dans des fichiers et consulté au besoin
  - mises à jour atomiques de Markdown sans réservation de fichiers
---

Harness fournit à chaque projet un environnement externe partagé par ses worktrees Git. Quinze skills indépendants couvrent le contexte, la planification modulaire, les transmissions, la coordination des agents et les procédures de développement. Les agents lisent uniquement les éléments nécessaires à leur tâche.

## Le contexte du projet en dehors du dépôt

Chaque dépôt ou monorepo possède un environnement. Les connaissances utiles résident dans des fichiers Markdown organisés par sujet. Les plans temporaires, la configuration des agents et le contexte de reprise existent uniquement au besoin ; les petites modifications individuelles ne nécessitent aucun dossier de travail.

## Des procédures ciblées et un contexte délimité

Les plans globaux sont modulaires quel que soit le nombre d’agents. Les équipes de réalisation et de revue peuvent référencer les mêmes livrables tout en conservant un contexte d’exécution distinct. Une transmission transfère la responsabilité par des références aux fichiers canoniques, sans recopier les conversations.

## Worktrees et persistance sûre

Les nouvelles worktrees résident dans l’environnement du projet. Les agents qui collaborent au sein d’une équipe peuvent alterner les écritures ; les équipes indépendantes utilisent des copies de travail distinctes. L’utilitaire Python protège les mises à jour Markdown contre l’écrasement de modifications intervenues depuis la lecture.

Une fois le travail terminé, les connaissances utiles sont consolidées et le contexte temporaire est supprimé. Les éléments encore nécessaires à une autre équipe ou à une transmission en attente restent disponibles. Le retrait d’une worktree est une décision séparée.
