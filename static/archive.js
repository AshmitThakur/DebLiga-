(function () {
    // Final official source of truth for Debate League 2025.
    const edition2025 = {
        winner: { team: 'Panel Pls Understand', leader: 'Sukhman' },
        pools: {
            'Pool A': [
                ['Panel Pls Understand', 3, 2, 1],
                ['Tappu Sena', 3, 2, 1],
                ['The Nexus', 3, 1, 2],
                ['Court of Reason', 3, 1, 2]
            ],
            'Pool B': [
                ['The Orators of Olympus', 3, 3, 0],
                ['Meow Meow', 3, 2, 1],
                ['Icarus', 3, 1, 2],
                ['Phuss Phuss Gang', 3, 0, 3]
            ]
        },
        knockouts: [
            { stage: 'Semifinal 1', winner: 'Panel Pls Understand', loser: 'The Orators of Olympus' },
            { stage: 'Semifinal 2', winner: 'Tappu Sena', loser: 'Meow Meow' },
            { stage: 'Third-place', winner: 'The Orators of Olympus', loser: 'Meow Meow', result: 'Third Place' },
            { stage: 'Final', winner: 'Panel Pls Understand', loser: 'Tappu Sena', result: 'Champion' }
        ],
        auction: {
            purse: 50000,
            teams: [
                { name: 'Tappu Sena', leader: 'Anshuman', squad: [['Pratham', 11500], ['Aaryav', 5000], ['Pranjal', 19500], ['Aashima', 10500]] },
                { name: 'Meow Meow', leader: 'Tanu', squad: [['Shriya', 18000], ['Barleen', 12000], ['Prabhleen', 10000], ['Saurabh', 10000]] },
                { name: 'Phuss Phuss Gang', leader: 'Jiteshwar', squad: [['Tanveer', 19000], ['Vivek', 9000], ['Prabhnoor', 14000], ['Naman', 8000]] },
                { name: 'The Nexus', leader: 'Ayan', squad: [['Nidhi', 7000], ['Ashmit', 29500], ['Jatin', 7000], ['Nandini', 6500]] },
                { name: 'Panel Pls Understand', leader: 'Sukhman', squad: [['Saniya', 30000], ['Ashmita', 8000], ['Jai', 6500], ['Javin', 5500]] },
                { name: 'Icarus', leader: 'Amrit', squad: [['Suhani', 13000], ['Ekam', 24000], ['Shivam', 6500], ['Aryan', 6500]] },
                { name: 'The Orators of Olympus', leader: 'Harsh', squad: [['Agam', 11500], ['Aadesh', 11000], ['Pankhuri', 14000], ['Ravneet', 13500]] },
                { name: 'Court of Reason', leader: 'Kamalpreet', squad: [['Samairah', 32500], ['Prisha', 6500], ['Swayam', 6000], ['Anjali', 5000]] }
            ]
        }
    };

    const teamEmojis = {
        'Panel Pls Understand': '🎤',
        'Tappu Sena': '⚔️',
        'The Nexus': '🔺',
        'Court of Reason': '⚖️',
        'The Orators of Olympus': '⚡',
        'Meow Meow': '🐱',
        'Icarus': '🪽',
        'Phuss Phuss Gang': '💨'
    };

    function teamName(name) {
        return (teamEmojis[name] ? teamEmojis[name] + ' ' : '') + name;
    }

    function currency(amount) {
        return amount.toLocaleString('en-IN') + ' points';
    }

    function poolCard(name, teams) {
        const rows = teams.map(function (team, index) {
            return `<tr><td><strong>${index + 1}</strong></td><td>${teamName(team[0])}</td><td>${team[1]}</td><td>${team[2]}</td><td>${team[3]}</td></tr>`;
        }).join('');
        return `<section class="archive-pool"><h3>${name}</h3><div class="archive-table-wrap"><table><thead><tr><th>Rank</th><th>Team</th><th>Played</th><th><span class="result-heading" title="Wins" aria-label="Wins">✓</span></th><th><span class="result-heading" title="Losses" aria-label="Losses">✕</span></th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
    }

    function knockoutCard(match) {
        const champion = match.result === 'Champion';
        const placement = match.result
            ? `<span class="archive-placement${champion ? ' archive-champion-line' : ''}">${champion ? '🏆 ' : ''}${match.result}: ${match.winner}</span>`
            : '';
        return `<article class="archive-match${champion ? ' archive-final-winner' : ''}"><p>${match.stage}</p><div><strong>${teamName(match.winner)}</strong><span>def.</span><span>${teamName(match.loser)}</span></div>${placement}</article>`;
    }

    function renderEditionArchive() {
        const select = document.getElementById('archive-year');
        const content = document.getElementById('archive-content');
        if (!select || !content) return;

        const year = '2025';
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year + ' Edition';
        select.appendChild(option);

        const pools = Object.keys(edition2025.pools).map(function (name) {
            return poolCard(name, edition2025.pools[name]);
        }).join('');
        content.innerHTML = `<header class="archive-edition-heading"><span>2025</span><div><p>Archived Edition</p><h3>Standings and knockout results</h3></div></header><div class="edition-champion-badge"><span>Debate League 2025 Winner</span><strong>🏆 Winning Team: ${edition2025.winner.team}</strong><small>Team Leader: ${edition2025.winner.leader}</small></div><div class="archive-pools">${pools}</div><section class="archive-knockouts"><h3>Knockouts</h3><div class="archive-match-grid">${edition2025.knockouts.map(knockoutCard).join('')}</div></section>`;
    }

    function renderAuction() {
        const host = document.querySelector('.auction-history-content[data-auction-year="2025"]');
        if (!host) return;

        const auction = edition2025.auction;
        const topPurchases = auction.teams
            .flatMap(function (team) {
                return team.squad.map(function (player) {
                    return { name: player[0], price: player[1] };
                });
            })
            .sort(function (a, b) { return b.price - a.price; })
            .slice(0, 5);

        const purchases = topPurchases.map(function (purchase, index) {
            return `<article class="top-purchase-card"><span>${index + 1}</span><div><strong>${purchase.name}</strong><small>${currency(purchase.price)}</small></div></article>`;
        }).join('');

        const teams = auction.teams.map(function (team) {
            const squad = team.squad.map(function (member) {
                return `<li><span>${member[0]}</span><strong>${currency(member[1])}</strong></li>`;
            }).join('');
            const total = team.squad.reduce(function (sum, member) {
                return sum + member[1];
            }, 0);
            return `<article class="auction-team-card"><header><h4>${teamName(team.name)}</h4><p>Team leader <strong>${team.leader}</strong></p></header><div class="auction-player-labels"><span>Player</span><span>Winning bid</span></div><ul>${squad}</ul><footer><span>Total spent</span><strong>${currency(total)}</strong><span>Remaining purse</span><strong>${currency(auction.purse - total)}</strong></footer></article>`;
        }).join('');

        host.innerHTML = `<section class="top-purchases"><div class="auction-subheading"><p>Highest Bids</p><h3>Top 5 Purchases of Debate League Auctions 2025</h3></div><div class="top-purchases-grid">${purchases}</div></section><section class="auction-snapshot"><div class="auction-subheading"><p>Team by Team</p><h3>All eight 2025 auction squads</h3></div><div class="auction-team-grid">${teams}</div></section><aside class="auction-matters"><div><p class="section-label">Why the Auction matters</p><h3>The season starts at the bidding table.</h3></div><ul><li>Strategy starts before the first round</li><li>Every bid changes team balance</li><li>Captains shape their identities through the auction</li><li>Great purchases often define great campaigns</li></ul></aside>`;
    }

    renderEditionArchive();
    renderAuction();
})();
