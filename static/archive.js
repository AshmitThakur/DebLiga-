(function () {
    const editions = {
        2025: {
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
                topPurchases: [
                    ['Samairah', 32500], ['Saniya', 30000], ['Ashmit', 29500],
                    ['Ekam', 24000], ['Pranjal', 19500]
                ],
                teams: [
                    { name: 'Panel Pls Understand', leader: 'Sukhman', squad: [['Saniya', 30000], ['Ashmita', 8000], ['Jai', 6500], ['Javin', 5500]] },
                    { name: 'Icarus', leader: 'Amrit', squad: [['Suhani', 13000], ['Ekam', 24000], ['Shivam', 6500], ['Avon', 6500]] },
                    { name: 'The Orators of Olympus', leader: 'Harsh', squad: [['Agam', 11500], ['Adesh', 11000], ['Pankhuri', 14000], ['Ravneet', 13500]] },
                    { name: 'Court of Reason', leader: 'Kamalpreet', squad: [['Samairah', 32500], ['Prisha', 6500], ['Swayam', 6000], ['Anjali', 5000]] },
                    { name: 'Meow Meow', leader: 'Tanu', squad: [['Shriya', 18000], ['Barleen', 12000], ['Prabhleen', 10000], ['Saurabh', 10000]] },
                    { name: 'Phuss Phuss Gang', leader: 'Jeetashwar', squad: [['Tanveer', 19000], ['Vivek', 9000], ['Prabhoor', 14000], ['Naman', 8000]] },
                    { name: 'The Nexus', leader: 'Ayan', squad: [['Nidhi', 7000], ['Ashmit', 29500], ['Jatin', 7500], ['Nandini', 6500]] },
                    { name: 'Tappu Sena', leader: 'Anshuman', squad: [['Pratham', 11500], ['Aurav', 6000], ['Pranjal', 19500], ['Aashima', 10500]] }
                ]
            }
        }
    };

    const select = document.getElementById('archive-year');
    const content = document.getElementById('archive-content');
    if (!select || !content) return;

    const teamEmojis = {
        'Panel Pls Understand': '\u{1F3A4}', 'Tappu Sena': '\u2694\uFE0F',
        'The Nexus': '\u{1F53A}', 'Court of Reason': '\u2696\uFE0F',
        'The Orators of Olympus': '\u26A1', 'Meow Meow': '\u{1F431}',
        'Icarus': '\u{1FABD}', 'Phuss Phuss Gang': '\u{1F4A8}'
    };
    function teamName(name) { return (teamEmojis[name] ? teamEmojis[name] + ' ' : '') + name; }

    Object.keys(editions).sort(function (a, b) { return b - a; }).forEach(function (year) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year + ' Edition';
        select.appendChild(option);
    });

    function poolCard(name, teams) {
        const rows = teams.map(function (team, index) {
            return `<tr><td><strong>${index + 1}</strong></td><td>${teamName(team[0])}</td><td>${team[1]}</td><td>${team[2]}</td><td>${team[3]}</td></tr>`;
        }).join('');
        return `<section class='archive-pool'><h3>${name}</h3><div class='archive-table-wrap'><table><thead><tr><th>Rank</th><th>Team</th><th>Played</th><th><span class='result-heading' title='Wins' aria-label='Wins'>✅</span></th><th><span class='result-heading' title='Losses' aria-label='Losses'>❌</span></th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
    }

    function knockoutCard(match) {
        const champion = match.result === 'Champion';
        const placement = match.result ? `<span class='archive-placement${champion ? ' archive-champion-line' : ''}'>${champion ? '🏆 ' : ''}${match.result}: ${match.winner}</span>` : '';
        return `<article class='archive-match${champion ? ' archive-final-winner' : ''}'><p>${match.stage}</p><div><strong>${teamName(match.winner)}</strong><span>def.</span><span>${teamName(match.loser)}</span></div>${placement}</article>`;
    }

    function render(year) {
        const edition = editions[year];
        const pools = Object.keys(edition.pools).map(function (name) { return poolCard(name, edition.pools[name]); }).join('');
        content.innerHTML = `<header class='archive-edition-heading'><span>${year}</span><div><p>Archived Edition</p><h3>Standings and knockout results</h3></div></header>${year === '2025' ? `<div class='edition-champion-badge'><span>Debate League 2025 Winner</span><strong>🏆 Panel Pls Understand</strong></div>` : ''}<div class='archive-pools'>${pools}</div><section class='archive-knockouts'><h3>Knockouts</h3><div class='archive-match-grid'>${edition.knockouts.map(knockoutCard).join('')}</div></section>`;
    }

    function renderAuction() {
        const host = document.querySelector('.auction-history-content');
        if (!host) return;
        const auction = editions[host.dataset.auctionYear].auction;
        const purchases = auction.topPurchases.map(function (purchase, index) {
            return `<article class='top-purchase-card'><span>${index + 1}</span><div><strong>${purchase[0]}</strong><small>${purchase[1].toLocaleString()} points</small></div></article>`;
        }).join('');
        const teams = auction.teams.map(function (team) {
            const squad = team.squad.map(function (member) {
                return `<li><span>${member[0]}</span><strong>₹${member[1].toLocaleString('en-IN')}</strong></li>`;
            }).join('');
            const total = team.squad.reduce(function (sum, member) { return sum + member[1]; }, 0);
            return `<article class='auction-team-card'><header><h4>${team.name}</h4><p>Leader <strong>${team.leader}</strong></p></header><div class='auction-player-labels'><span>Player</span><span>Winning bid</span></div><ul>${squad}</ul><footer><span>Total spent</span><strong>₹${total.toLocaleString('en-IN')}</strong><span>Remaining purse</span><strong>₹${Math.max(0, 50000 - total).toLocaleString('en-IN')}</strong></footer></article>`;
        }).join('');
        host.innerHTML = `<section class='top-purchases'><div class='auction-subheading'><p>Highest Bids</p><h3>Top 5 Purchases of Debate League Auctions 2025</h3></div><div class='top-purchases-grid'>${purchases}</div></section><section class='auction-snapshot'><div class='auction-subheading'><p>Team by Team</p><h3>Auction Snapshot</h3></div><div class='auction-team-grid'>${teams}</div></section><aside class='auction-matters'><div><p class='section-label'>Why the Auction matters</p><h3>The season starts at the bidding table.</h3></div><ul><li>Strategy starts before the first round</li><li>Every bid changes team balance</li><li>Captains shape their identities through the auction</li><li>Great purchases often define great campaigns</li></ul></aside>`;
    }

    select.addEventListener('change', function () { render(select.value); });
    render(select.value);
    renderAuction();
})();
