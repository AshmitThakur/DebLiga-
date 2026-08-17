const state = {
  pools: [],
  teams: [],
  speakers: [],
  rounds: [],
  debates: [],
  schedule: [],
  auctionTeams: [],
};

const $ = (id) => document.getElementById(id);
const messageBox = $("message");
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[character]);

function showMessage(text, isError = false) {
  messageBox.textContent = text;
  messageBox.dataset.type = isError ? "error" : "success";
}

async function api(url, options = {}) {
  const response = await fetch(url, options);

  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const detail = data?.detail || "Something went wrong";

    throw new Error(
      typeof detail === "string"
        ? detail
        : JSON.stringify(detail)
    );
  }

  return data;
}

function poolName(poolId) {
  return (
    state.pools.find((p) => p.id === poolId)?.name
    || `Pool ${poolId}`
  );
}

function teamName(teamId) {
  const team = state.teams.find((t) => t.id === teamId);
  return team
    ? `${team.emoji ? `${team.emoji} ` : ""}${team.name}`
    : `Team ${teamId}`;
}

function teamHtml(team, fallback = "?") {
  if (!team) return escapeHtml(fallback);
  const emoji = team.emoji
    ? `<span class="team-emoji" aria-hidden="true">${escapeHtml(team.emoji)}</span>`
    : "";
  return `<span class="team-name-lock">${emoji}<span class="team-name">${escapeHtml(team.name)}</span></span>`;
}

function teamHtmlById(teamId) {
  return teamHtml(
    state.teams.find((team) => team.id === teamId),
    `Team ${teamId}`
  );
}

function roundName(roundId) {
  const round = state.rounds.find(
    (r) => r.id === roundId
  );

  return round
    ? `Round ${round.number}`
    : `Round ${roundId}`;
}

function stageName(stage) {
  return {
    pool: "Pool Stage",
    semifinal: "Semifinal",
    third_place: "Third Place",
    final: "Final",
  }[stage] || stage;
}

function jsonOptions(method, body) {
  return {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  };
}

function fillSelect(
  select,
  items,
  getValue,
  getLabel,
  placeholder = null
) {
  select.innerHTML = "";

  if (placeholder !== null) {
    const option = document.createElement("option");

    option.value = "";
    option.textContent = placeholder;

    select.appendChild(option);
  }

  items.forEach((item) => {
    const option = document.createElement("option");

    option.value = getValue(item);
    option.textContent = getLabel(item);

    select.appendChild(option);
  });
}


// ==================================================
// LOAD EVERYTHING
// ==================================================

async function loadAll() {
  try {
    const [
      pools,
      teams,
      speakers,
      rounds,
      debates,
      schedule,
    ] = await Promise.all([
      api("/api/pools"),
      api("/api/teams"),
      api("/api/speakers"),
      api("/api/rounds"),
      api("/api/debates"),
      api("/api/schedule"),
    ]);

    state.pools = pools;
    state.teams = teams;
    state.speakers = speakers;
    state.rounds = rounds;
    state.debates = debates;
    state.schedule = schedule;

    populateForms();

    renderSummary();
    renderPools();
    renderTeams();
    renderSpeakers();
    renderRounds();
    renderDebates();
    renderKnockouts();
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// DROPDOWNS
// ==================================================

function populateForms() {
  fillSelect(
    $("team-pool"),
    state.pools,
    (pool) => pool.id,
    (pool) => pool.name
  );

  [
    $("speaker-team"),
    $("debate-team1"),
    $("debate-team2"),
  ].forEach((select) => {
    fillSelect(
      select,
      state.teams,
      (team) => team.id,
      (team) =>
        `${teamName(team.id)} (${poolName(team.pool_id)})`
    );
  });

  fillSelect(
    $("debate-round"),
    [...state.rounds].sort(
      (a, b) => a.number - b.number
    ),
    (round) => round.id,
    (round) => `Round ${round.number}`
  );

  fillSelect(
    $("result-debate"),
    state.debates,
    (debate) => debate.id,
    (debate) =>
      `${stageName(debate.stage)} - `
      + `${roundName(debate.round_id)} - `
      + `${teamName(debate.team1_id)} `
      + `vs ${teamName(debate.team2_id)}`,
    "Select Debate"
  );

  $("result-winner").innerHTML = "";
}


// ==================================================
// DASHBOARD SUMMARY
// ==================================================

function renderSummary() {
  const poolDebates =
    state.debates.filter(
      (debate) =>
        debate.stage === "pool"
    ).length;

  const completed =
    state.debates.filter(
      (debate) =>
        debate.winner_team_id !== null
    ).length;

  $("summary").innerHTML = `
    <p>
      <strong>${state.pools.length}</strong>
      Pools |

      <strong>${state.teams.length}</strong>
      Teams |

      <strong>${state.speakers.length}</strong>
      Speakers |

      <strong>${state.rounds.length}</strong>
      Rounds |

      <strong>${state.debates.length}</strong>
      Debates
    </p>

    <p>
      Pool debates:
      <strong>${poolDebates}</strong>

      |

      Results completed:
      <strong>${completed}</strong>
    </p>
  `;
}


// ==================================================
// POOLS TABLE
// ==================================================

function renderPools() {
  if (!state.pools.length) {
    $("pool-list").innerHTML =
      "<p>No pools yet.</p>";

    return;
  }

  $("pool-list").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Pool</th>
          <th>Teams</th>
          <th>Actions</th>
        </tr>
      </thead>

      <tbody>

        ${state.pools
          .map((pool) => {
            const count =
              state.teams.filter(
                (team) =>
                  team.pool_id === pool.id
              ).length;

            return `
              <tr>
                <td>${pool.id}</td>

                <td>
                  ${pool.name}
                </td>

                <td>
                  ${count}
                </td>

                <td>
                  <button
                    onclick="editPool(${pool.id})"
                  >
                    Edit
                  </button>

                  <button
                    onclick="deletePool(${pool.id})"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            `;
          })
          .join("")}

      </tbody>
    </table>
  `;
}


// ==================================================
// TEAMS TABLE
// ==================================================

function renderTeams() {
  if (!state.teams.length) {
    $("team-list").innerHTML =
      "<p>No teams yet.</p>";

    return;
  }

  $("team-list").innerHTML = `
    <table>

      <thead>
        <tr>
          <th>ID</th>
          <th>Team</th>
          <th>Pool</th>
          <th>Speakers</th>
          <th>Actions</th>
        </tr>
      </thead>

      <tbody>

        ${state.teams
          .map((team) => {
            const count =
              state.speakers.filter(
                (speaker) =>
                  speaker.team_id === team.id
              ).length;

            return `
              <tr>

                <td>
                  ${team.id}
                </td>

                <td>
                  <a
                    href="/teams/${team.id}"
                    target="_blank"
                  >
                    ${teamHtml(team)}
                  </a>
                </td>

                <td>
                  ${poolName(team.pool_id)}
                </td>

                <td>
                  ${count}
                </td>

                <td>

                  <button
                    onclick="editTeam(${team.id})"
                  >
                    Edit
                  </button>

                  <button
                    onclick="deleteTeam(${team.id})"
                  >
                    Delete
                  </button>

                </td>

              </tr>
            `;
          })
          .join("")}

      </tbody>

    </table>
  `;
}


// ==================================================
// SPEAKERS TABLE
// ==================================================

function renderSpeakers() {
  if (!state.speakers.length) {
    $("speaker-list").innerHTML =
      "<p>No speakers yet.</p>";

    return;
  }

  $("speaker-list").innerHTML = `
    <table>

      <thead>
        <tr>
          <th>ID</th>
          <th>Speaker</th>
          <th>Team</th>
          <th>Actions</th>
        </tr>
      </thead>

      <tbody>

        ${state.speakers
          .map(
            (speaker) => `
              <tr>

                <td>
                  ${speaker.id}
                </td>

                <td>
                  <a
                    href="/speakers/${speaker.id}"
                    target="_blank"
                  >
                    ${speaker.name}
                  </a>
                </td>

                <td>
                  ${teamHtmlById(speaker.team_id)}
                </td>

                <td>

                  <button
                    onclick="editSpeaker(${speaker.id})"
                  >
                    Edit
                  </button>

                  <button
                    onclick="deleteSpeaker(${speaker.id})"
                  >
                    Delete
                  </button>

                </td>

              </tr>
            `
          )
          .join("")}

      </tbody>

    </table>
  `;
}


// ==================================================
// ROUNDS TABLE
// ==================================================

function renderRounds() {
  if (!state.rounds.length) {
    $("round-list").innerHTML =
      "<p>No rounds yet.</p>";

    return;
  }

  const rounds =
    [...state.rounds].sort(
      (a, b) =>
        a.number - b.number
    );

  $("round-list").innerHTML = `
    <table>

      <thead>

        <tr>
          <th>ID</th>
          <th>Round</th>
          <th>Motion</th>
          <th>Actions</th>
        </tr>

      </thead>

      <tbody>

        ${rounds
          .map(
            (round) => `
              <tr>

                <td>
                  ${round.id}
                </td>

                <td>
                  Round ${round.number}
                </td>

                <td>
                  ${round.motion || "Not set"}
                </td>

                <td>

                  <button
                    onclick="editRound(${round.id})"
                  >
                    Edit
                  </button>

                  <button
                    onclick="deleteRound(${round.id})"
                  >
                    Delete
                  </button>

                </td>

              </tr>
            `
          )
          .join("")}

      </tbody>

    </table>
  `;
}


// ==================================================
// DEBATES TABLE
// ==================================================

function renderDebates() {
  if (!state.schedule.length) {
    $("debate-list").innerHTML =
      "<p>No debates yet.</p>";

    return;
  }

  $("debate-list").innerHTML = `
    <table>

      <thead>

        <tr>
          <th>ID</th>
          <th>Stage</th>
          <th>Date</th>
          <th>Debate</th>
          <th>Pool</th>
          <th>Matchup</th>
          <th>Room</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>

      </thead>

      <tbody>

        ${state.schedule
          .map(
            (item) => `
              <tr>

                <td>
                  ${item.debate_id}
                </td>

                <td>
                  ${item.stage_name}
                </td>

                <td>
                  ${
                    item.date_label
                      ? `${item.day}, ${item.date_label}`
                      : "-"
                  }
                </td>

                <td>
                  ${item.debate_number ? `Debate ${item.debate_number}` : (item.round_number ? `Round ${item.round_number}` : "-")}
                </td>

                <td>
                  ${item.pool || "-"}
                </td>

                <td>
                  ${teamHtml(item.team1)}
                  ${item.team1?.side ? `(${escapeHtml(item.team1.side)})` : ""}
                  vs
                  ${teamHtml(item.team2)}
                  ${item.team2?.side ? `(${escapeHtml(item.team2.side)})` : ""}
                </td>

                <td>
                  ${item.room || "TBA"}
                </td>

                <td>
                  ${
                    item.winner
                      ? `Winner: ${teamHtml(item.winner)}${
                          item.team1?.average_score != null
                          && item.team2?.average_score != null
                            ? `<br>Avg: ${Number(item.team1.average_score).toFixed(2)} - ${Number(item.team2.average_score).toFixed(2)}`
                            : ""
                        }`
                      : "Pending"
                  }
                </td>

                <td>

                  <button
                    onclick="selectResultDebate(${item.debate_id})"
                  >
                    Result
                  </button>

                  <button
                    onclick="editDebate(${item.debate_id})"
                  >
                    Edit
                  </button>

                  <button
                    onclick="clearDebateResult(${item.debate_id})"
                  >
                    Clear Result
                  </button>

                  <button
                    onclick="deleteDebate(${item.debate_id})"
                  >
                    Delete
                  </button>

                </td>

              </tr>
            `
          )
          .join("")}

      </tbody>

    </table>
  `;
}


// ==================================================
// KNOCKOUTS
// ==================================================

function renderKnockouts() {
  const knockouts =
    state.schedule.filter(
      (item) =>
        item.stage !== "pool"
    );

  if (!knockouts.length) {
    $("knockout-list").innerHTML = `
      <p>
        Knockout stage has not been generated yet.
      </p>
    `;

    return;
  }

  $("knockout-list").innerHTML = `
    <h3>
      Current Knockout Matches
    </h3>

    ${knockouts
      .map(
        (item) => `
          <div class="knockout-match">

            <strong>
              ${item.stage_name}
            </strong>

            <p>
              ${teamHtml(item.team1, "TBD")}
              vs
              ${teamHtml(item.team2, "TBD")}
            </p>

            <p>
              ${
                item.winner
                  ? `Winner: ${teamHtml(item.winner)}`
                  : "Result Pending"
              }
            </p>

            <button
              onclick="selectResultDebate(${item.debate_id})"
            >
              Enter / Edit Result
            </button>

          </div>
        `
      )
      .join("")}
  `;
}


// ==================================================
// CREATE POOL
// ==================================================

$("pool-form").addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    try {
      await api(
        "/api/pools",
        jsonOptions(
          "POST",
          {
            name:
              $("pool-name")
                .value
                .trim(),
          }
        )
      );

      event.target.reset();

      showMessage(
        "Pool added"
      );

      await loadAll();
    } catch (error) {
      showMessage(
        error.message,
        true
      );
    }
  }
);


// ==================================================
// CREATE TEAM
// ==================================================

$("team-form").addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    try {
      await api(
        "/api/teams",
        jsonOptions(
          "POST",
          {
            name:
              $("team-name")
                .value
                .trim(),

            pool_id:
              Number(
                $("team-pool").value
              ),
          }
        )
      );

      event.target.reset();

      showMessage(
        "Team added"
      );

      await loadAll();
    } catch (error) {
      showMessage(
        error.message,
        true
      );
    }
  }
);


// ==================================================
// CREATE SPEAKER
// ==================================================

$("speaker-form").addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    try {
      await api(
        "/api/speakers",
        jsonOptions(
          "POST",
          {
            name:
              $("speaker-name")
                .value
                .trim(),

            team_id:
              Number(
                $("speaker-team").value
              ),
          }
        )
      );

      event.target.reset();

      showMessage(
        "Speaker added"
      );

      await loadAll();
    } catch (error) {
      showMessage(
        error.message,
        true
      );
    }
  }
);


// ==================================================
// CREATE ROUND
// ==================================================

$("round-form").addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    try {
      const motion =
        $("round-motion")
          .value
          .trim();

      await api(
        "/api/rounds",
        jsonOptions(
          "POST",
          {
            number:
              Number(
                $("round-number").value
              ),

            motion:
              motion || null,
          }
        )
      );

      event.target.reset();

      showMessage(
        "Round created"
      );

      await loadAll();
    } catch (error) {
      showMessage(
        error.message,
        true
      );
    }
  }
);


// ==================================================
// CREATE DEBATE
// ==================================================

$("debate-form").addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    try {
      const room =
        $("debate-room")
          .value
          .trim();

      await api(
        "/api/debates",
        jsonOptions(
          "POST",
          {
            round_id:
              Number(
                $("debate-round").value
              ),

            team1_id:
              Number(
                $("debate-team1").value
              ),

            team2_id:
              Number(
                $("debate-team2").value
              ),

            room:
              room || null,

            stage:
              $("debate-stage").value,
          }
        )
      );

      event.target.reset();

      showMessage(
        "Debate created"
      );

      await loadAll();
    } catch (error) {
      showMessage(
        error.message,
        true
      );
    }
  }
);


// ==================================================
// EDIT POOL
// ==================================================

async function editPool(poolId) {
  const pool =
    state.pools.find(
      (pool) =>
        pool.id === poolId
    );

  if (!pool) {
    return;
  }

  const name =
    prompt(
      "Pool name:",
      pool.name
    );

  if (!name?.trim()) {
    return;
  }

  try {
    await api(
      `/api/pools/${poolId}`,
      jsonOptions(
        "PUT",
        {
          name: name.trim(),
        }
      )
    );

    showMessage(
      "Pool updated"
    );

    await loadAll();
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// DELETE POOL
// ==================================================

async function deletePool(poolId) {
  if (
    !confirm(
      "Delete this pool?"
    )
  ) {
    return;
  }

  try {
    await api(
      `/api/pools/${poolId}`,
      {
        method: "DELETE",
      }
    );

    showMessage(
      "Pool deleted"
    );

    await loadAll();
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// EDIT TEAM
// ==================================================

async function editTeam(teamId) {
  const team =
    state.teams.find(
      (team) =>
        team.id === teamId
    );

  if (!team) {
    return;
  }

  const newName =
    prompt(
      "Team name:",
      team.name
    );

  if (!newName?.trim()) {
    return;
  }

  const poolOptions =
    state.pools
      .map(
        (pool) =>
          `${pool.id} = ${pool.name}`
      )
      .join("\n");

  const newPoolId =
    Number(
      prompt(
        `Pool ID:\n${poolOptions}`,
        team.pool_id
      )
    );

  if (!newPoolId) {
    return;
  }

  try {
    await api(
      `/api/teams/${teamId}`,
      jsonOptions(
        "PUT",
        {
          name:
            newName.trim(),

          pool_id:
            newPoolId,
        }
      )
    );

    showMessage(
      "Team updated"
    );

    await loadAll();
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// DELETE TEAM
// ==================================================

async function deleteTeam(teamId) {
  if (
    !confirm(
      "Delete this team?"
    )
  ) {
    return;
  }

  try {
    await api(
      `/api/teams/${teamId}`,
      {
        method: "DELETE",
      }
    );

    showMessage(
      "Team deleted"
    );

    await loadAll();
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// EDIT SPEAKER
// ==================================================

async function editSpeaker(speakerId) {
  const speaker =
    state.speakers.find(
      (speaker) =>
        speaker.id === speakerId
    );

  if (!speaker) {
    return;
  }

  const newName =
    prompt(
      "Speaker name:",
      speaker.name
    );

  if (!newName?.trim()) {
    return;
  }

  const teamOptions =
    state.teams
      .map(
        (team) =>
          `${team.id} = ${teamName(team.id)}`
      )
      .join("\n");

  const newTeamId =
    Number(
      prompt(
        `Team ID:\n${teamOptions}`,
        speaker.team_id
      )
    );

  if (!newTeamId) {
    return;
  }

  try {
    await api(
      `/api/speakers/${speakerId}`,
      jsonOptions(
        "PUT",
        {
          name:
            newName.trim(),

          team_id:
            newTeamId,
        }
      )
    );

    showMessage(
      "Speaker updated"
    );

    await loadAll();
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// DELETE SPEAKER
// ==================================================

async function deleteSpeaker(speakerId) {
  if (
    !confirm(
      "Delete this speaker?"
    )
  ) {
    return;
  }

  try {
    await api(
      `/api/speakers/${speakerId}`,
      {
        method: "DELETE",
      }
    );

    showMessage(
      "Speaker deleted"
    );

    await loadAll();
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// EDIT ROUND
// ==================================================

async function editRound(roundId) {
  const round =
    state.rounds.find(
      (round) =>
        round.id === roundId
    );

  if (!round) {
    return;
  }

  const number =
    Number(
      prompt(
        "Round number:",
        round.number
      )
    );

  if (!number) {
    return;
  }

  const motion =
    prompt(
      "Motion:",
      round.motion || ""
    );

  if (motion === null) {
    return;
  }

  try {
    await api(
      `/api/rounds/${roundId}`,
      jsonOptions(
        "PUT",
        {
          number,

          motion:
            motion.trim()
            || null,
        }
      )
    );

    showMessage(
      "Round updated"
    );

    await loadAll();
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// DELETE ROUND
// ==================================================

async function deleteRound(roundId) {
  if (
    !confirm(
      "Delete this round?"
    )
  ) {
    return;
  }

  try {
    await api(
      `/api/rounds/${roundId}`,
      {
        method: "DELETE",
      }
    );

    showMessage(
      "Round deleted"
    );

    await loadAll();
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// EDIT DEBATE
// ==================================================

async function editDebate(debateId) {
  const debate =
    state.debates.find(
      (debate) =>
        debate.id === debateId
    );

  if (!debate) {
    return;
  }

  const roundOptions =
    state.rounds
      .map(
        (round) =>
          `${round.id} = Round ${round.number}`
      )
      .join("\n");

  const teamOptions =
    state.teams
      .map(
        (team) =>
          `${team.id} = ${teamName(team.id)}`
      )
      .join("\n");

  const roundId =
    Number(
      prompt(
        `Round ID:\n${roundOptions}`,
        debate.round_id
      )
    );

  if (!roundId) {
    return;
  }

  const team1Id =
    Number(
      prompt(
        `Team 1 ID:\n${teamOptions}`,
        debate.team1_id
      )
    );

  if (!team1Id) {
    return;
  }

  const team2Id =
    Number(
      prompt(
        `Team 2 ID:\n${teamOptions}`,
        debate.team2_id
      )
    );

  if (!team2Id) {
    return;
  }

  const room =
    prompt(
      "Room:",
      debate.room || ""
    );

  if (room === null) {
    return;
  }

  const stage =
    prompt(
      "Stage: pool / semifinal / third_place / final",
      debate.stage
    );

  if (!stage?.trim()) {
    return;
  }

  try {
    await api(
      `/api/debates/${debateId}`,
      jsonOptions(
        "PUT",
        {
          round_id:
            roundId,

          team1_id:
            team1Id,

          team2_id:
            team2Id,

          room:
            room.trim()
            || null,

          stage:
            stage
              .trim()
              .toLowerCase(),
        }
      )
    );

    showMessage(
      "Debate updated"
    );

    await loadAll();
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// DELETE DEBATE
// ==================================================

async function deleteDebate(debateId) {
  if (
    !confirm(
      "Delete this debate and its result?"
    )
  ) {
    return;
  }

  try {
    await api(
      `/api/debates/${debateId}`,
      {
        method: "DELETE",
      }
    );

    showMessage(
      "Debate deleted"
    );

    await loadAll();
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// RESULT DEBATE SELECT
// ==================================================

$("result-debate").addEventListener(
  "change",
  async (event) => {
    const debateId =
      Number(
        event.target.value
      );

    if (!debateId) {
      $("result-winner").innerHTML = "";

      $("result-speakers").innerHTML =
        "Select a debate first.";

      return;
    }

    await loadResultForm(
      debateId
    );
  }
);


// ==================================================
// SELECT RESULT FROM DEBATE TABLE
// ==================================================

async function selectResultDebate(debateId) {
  $("result-debate").value =
    String(debateId);

  await loadResultForm(
    debateId
  );

  $("result-form").scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}


// ==================================================
// LOAD EXISTING RESULT
// ==================================================

async function loadResultForm(debateId) {
  try {
    const debate =
      state.debates.find(
        (debate) =>
          debate.id === debateId
      );

    if (!debate) {
      return;
    }

    const team1 =
      state.teams.find(
        (team) =>
          team.id === debate.team1_id
      );

    const team2 =
      state.teams.find(
        (team) =>
          team.id === debate.team2_id
      );

    $("result-winner").innerHTML = "";

    [team1, team2].forEach(
      (team) => {
        if (!team) {
          return;
        }

        const option =
          document.createElement(
            "option"
          );

        option.value =
          team.id;

        option.textContent =
          teamName(team.id);

        $("result-winner")
          .appendChild(option);
      }
    );

    const current =
      await api(
        `/api/debates/${debateId}/result`
      );

    if (
      current.winner_team_id !== null
    ) {
      $("result-winner").value =
        String(
          current.winner_team_id
        );
    }

    const performanceMap =
      new Map(
        current.performances.map(
          (performance) => [
            performance.speaker_id,
            performance,
          ]
        )
      );

    const speakers =
      state.speakers.filter(
        (speaker) =>
          speaker.team_id === debate.team1_id
          ||
          speaker.team_id === debate.team2_id
      );

    if (!speakers.length) {
      $("result-speakers").innerHTML = `
        <p>
          Add speakers to these teams
          before entering scores.
        </p>
      `;

      return;
    }

    $("result-speakers").innerHTML =
      speakers
        .map(
          (speaker) => {
            const existing =
              performanceMap.get(
                speaker.id
              );

            return `
              <div class="result-speaker-row">

                <p>
                  <strong>
                    ${speaker.name}
                  </strong>

                  —

                  ${teamHtmlById(speaker.team_id)}
                </p>

                <input
                  class="speaker-role"
                  data-speaker-id="${speaker.id}"
                  type="text"
                  placeholder="Role"
                  value="${existing?.role || ""}"
                >

                <input
                  class="speaker-score"
                  data-speaker-id="${speaker.id}"
                  type="number"
                  step="0.01"
                  placeholder="Score"
                  value="${existing?.score ?? ""}"
                >

              </div>
            `;
          }
        )
        .join("");
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// SAVE / UPDATE RESULT
// ==================================================

$("result-form").addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    const debateId =
      Number(
        $("result-debate").value
      );

    const winnerTeamId =
      Number(
        $("result-winner").value
      );

    if (!debateId) {
      showMessage(
        "Select a debate",
        true
      );

      return;
    }

    const performances = [];

    document
      .querySelectorAll(
        ".speaker-score"
      )
      .forEach(
        (scoreInput) => {
          if (
            scoreInput.value === ""
          ) {
            return;
          }

          const speakerId =
            Number(
              scoreInput.dataset
                .speakerId
            );

          const roleInput =
            document.querySelector(
              `.speaker-role[data-speaker-id="${speakerId}"]`
            );

          performances.push({
            speaker_id:
              speakerId,

            role:
              roleInput.value.trim()
              || "Speaker",

            score:
              Number(
                scoreInput.value
              ),
          });
        }
      );

    try {
      await api(
        `/api/debates/${debateId}/result`,
        jsonOptions(
          "POST",
          {
            winner_team_id:
              winnerTeamId,

            performances,
          }
        )
      );

      showMessage(
        "Result saved"
      );

      await loadAll();

      $("result-debate").value =
        String(debateId);

      await loadResultForm(
        debateId
      );
    } catch (error) {
      showMessage(
        error.message,
        true
      );
    }
  }
);


// ==================================================
// CLEAR RESULT BUTTON
// ==================================================

$("clear-result-button")
  .addEventListener(
    "click",
    async () => {
      const debateId =
        Number(
          $("result-debate").value
        );

      if (!debateId) {
        showMessage(
          "Select a debate first",
          true
        );

        return;
      }

      await clearDebateResult(
        debateId
      );
    }
  );


// ==================================================
// CLEAR DEBATE RESULT
// ==================================================

async function clearDebateResult(debateId) {
  if (
    !confirm(
      "Clear winner and all speaker scores for this debate?"
    )
  ) {
    return;
  }

  try {
    await api(
      `/api/debates/${debateId}/result`,
      {
        method: "DELETE",
      }
    );

    showMessage(
      "Result cleared"
    );

    await loadAll();

    $("result-debate").value =
      String(debateId);

    await loadResultForm(
      debateId
    );
  } catch (error) {
    showMessage(
      error.message,
      true
    );
  }
}


// ==================================================
// GENERATE KNOCKOUTS
// ==================================================

$("generate-knockouts")
  .addEventListener(
    "click",
    async () => {
      try {
        const result =
          await api(
            "/api/knockouts/generate",
            {
              method: "POST",
            }
          );

        showMessage(
          result.message
        );

        await loadAll();
      } catch (error) {
        showMessage(
          error.message,
          true
        );
      }
    }
  );


// ==================================================
// RESET KNOCKOUTS
// ==================================================

$("reset-knockouts")
  .addEventListener(
    "click",
    async () => {
      if (
        !confirm(
          "Delete all semifinals, final and third-place match?"
        )
      ) {
        return;
      }

      try {
        const result =
          await api(
            "/api/knockouts",
            {
              method: "DELETE",
            }
          );

        showMessage(
          result.message
        );

        await loadAll();
      } catch (error) {
        showMessage(
          error.message,
          true
        );
      }
    }
  );


// ==================================================
// START DASHBOARD
// ==================================================

function auctionPlayerRow(player = {}) {
  const row = document.createElement("div"); row.className = "auction-player-input";
  row.innerHTML = `<input class="auction-player-name" placeholder="Player name" value="${escapeHtml(player.name || "")}" required><input class="auction-player-price" type="number" min="0" step="1" placeholder="Price" value="${player.price ?? ""}" required><button type="button" class="remove-auction-player">Remove</button>`;
  row.querySelector(".remove-auction-player").onclick = () => { row.remove(); updateAuctionTotal(); };
  row.querySelector(".auction-player-price").oninput = updateAuctionTotal;
  $("auction-player-fields").appendChild(row);
}
function updateAuctionTotal() { const total = [...document.querySelectorAll(".auction-player-price")].reduce((sum, input) => sum + (Number(input.value) || 0), 0); $("auction-live-total").textContent = `Total: ${total.toLocaleString("en-IN")} points · Remaining: ${(50000-total).toLocaleString("en-IN")} points`; $("auction-live-total").dataset.invalid = total > 50000 ? "true" : "false"; }
function resetAuctionForm() { $("auction-team-form").reset(); $("auction-team-id").value = ""; $("auction-player-fields").innerHTML = ""; $("cancel-auction-edit").hidden = true; auctionPlayerRow(); updateAuctionTotal(); }
async function loadAuctionTeams() { state.auctionTeams = await api("/api/admin/auctions/2026/teams"); $("auction-team-list").innerHTML = state.auctionTeams.map(t => `<article class="admin-list-item"><div><strong>${teamHtml({name:t.team_name,emoji:t.display_emoji},t.team_name)}</strong><small>${escapeHtml(t.leader_name)} · ${t.players.length} players · ${t.total_spent.toLocaleString("en-IN")} points spent</small></div><div><button type="button" onclick="editAuctionTeam(${t.id})">Edit</button><button type="button" onclick="deleteAuctionTeam(${t.id})">Delete</button></div></article>`).join("") || "<p>No 2026 auction teams added yet.</p>"; }
function editAuctionTeam(id) { const t = state.auctionTeams.find(x => x.id === id); if (!t) return; $("auction-team-id").value=t.id; $("auction-team-name").value=t.team_name; $("auction-leader-name").value=t.leader_name; $("auction-accent").value=t.accent_color || "#d6a62e"; $("auction-player-fields").innerHTML=""; t.players.forEach(auctionPlayerRow); $("cancel-auction-edit").hidden=false; updateAuctionTotal(); $("auction-team-form").scrollIntoView({behavior:"smooth"}); }
async function deleteAuctionTeam(id) { if (!confirm("Delete this auction team and its players?")) return; try { await api(`/api/admin/auctions/2026/teams/${id}`, {method:"DELETE"}); showMessage("Auction team deleted"); await loadAuctionTeams(); } catch(e) { showMessage(e.message,true); } }
$("add-auction-player").onclick = () => auctionPlayerRow(); $("cancel-auction-edit").onclick=resetAuctionForm;
$("auction-team-form").onsubmit = async event => { event.preventDefault(); const id=$("auction-team-id").value; const players=[...document.querySelectorAll(".auction-player-input")].map(row=>({name:row.querySelector(".auction-player-name").value.trim(),price:Number(row.querySelector(".auction-player-price").value)})); try { await api(id?`/api/admin/auctions/2026/teams/${id}`:"/api/admin/auctions/2026/teams",jsonOptions(id?"PUT":"POST",{team_name:$("auction-team-name").value.trim(),leader_name:$("auction-leader-name").value.trim(),accent_color:$("auction-accent").value,players})); showMessage(id?"Auction team updated":"Auction team added"); resetAuctionForm(); await loadAuctionTeams(); } catch(e) { showMessage(e.message,true); } };
resetAuctionForm(); loadAuctionTeams().catch(e=>showMessage(e.message,true));

loadAll();
