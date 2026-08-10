// The most common ruleset for Cabo. House rules vary — edit freely.

export const rulesSections = [
  {
    title: 'Objective',
    body: 'End the game with the lowest total score across all rounds. Each round, you want the lowest combined value of the cards in front of you — and the lowest total after all rounds wins the game.',
  },
  {
    title: 'Setup',
    body: '2–6 players. Each player is dealt 4 cards, placed face down in a row in front of them without looking. At the very start of the round, each player may peek at only their two bottom-row cards (the two closest to them) once, then must remember their positions for the rest of the round.',
  },
  {
    title: 'Card Values',
    body: 'Ace = 1. Number cards 2–10 = face value. Jack = 11. Queen = 12. Red King (hearts/diamonds) = 0. Black King (clubs/spades) = 13. Joker = 0.',
  },
  {
    title: 'Your Turn',
    body: 'Draw the top card from the draw pile or take the top card of the discard pile. If you drew from the draw pile, you may either discard it, or swap it for one of your own face-down cards (discarding the card you swap out, still unseen by you). If the drawn card is a 7, 8, 9, 10, Jack, Queen, or King, you may use its special power (below) instead of swapping — then discard it.',
  },
  {
    title: 'Special Powers',
    body: '7 or 8: peek at one of your own cards. 9 or 10: peek at one opponent’s card. Jack or Queen: blind swap — swap any two cards on the table (yours or an opponent’s) without looking at either. King: look at any one card on the table, then choose whether to swap it with another card.',
  },
  {
    title: 'Calling "Cabo"',
    body: 'On your turn, instead of drawing, you may call "Cabo" if you believe you have the lowest hand. Play continues one final time around the table (every other player still gets one last turn), then everyone reveals their cards.',
  },
  {
    title: 'End of Round Scoring',
    body: 'Everyone reveals and adds up their 4 cards. If the player who called Cabo has the strictly lowest hand, they score 0 for the round. If they don’t (including ties for lowest), they score their hand total plus a penalty (5 points by default). Every other player simply scores their hand total. All scores are added to each player’s running total.',
  },
  {
    title: 'Winning the Game',
    body: 'Play continues round after round until a player’s total score reaches the target (100 points by default). The game then ends immediately, and whoever has the lowest total score across all rounds wins — even if it isn’t the player who crossed the target.',
  },
]
