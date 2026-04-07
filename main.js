/**
 * OEMS — Main Page JavaScript
 * Used on the Take Exam page.
 *
 * FEATURES:
 * 1. Countdown timer (auto-submits when it reaches 0:00)
 * 2. Live answer progress tracker
 *
 * VIVA EXPLANATION:
 * "I use setInterval to run a function every 1000ms (1 second)
 * which decrements a counter and updates the display.
 * When it reaches zero, the form is submitted automatically."
 */

document.addEventListener('DOMContentLoaded', function() {

  /* ──────────────────────────────────────────────────────────
     1. EXAM COUNTDOWN TIMER
  ────────────────────────────────────────────────────────── */

  const timerEl = document.getElementById('time-remaining');
  const examForm = document.getElementById('exam-form');

  if (timerEl && examForm) {

    // Get exam duration from the data attribute on the timer element
    const durationMinutes = parseInt(timerEl.dataset.duration) || 30;
    let secondsLeft = durationMinutes * 60;  // convert to seconds

    // Format seconds into "MM:SS" display
    function formatTime(seconds) {
      var minutes = Math.floor(seconds / 60);
      var secs    = seconds % 60;
      return String(minutes).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
    }

    // Called every second
    function tick() {
      timerEl.textContent = formatTime(secondsLeft);

      // Color changes as time runs out
      if      (secondsLeft <= 60)  timerEl.style.color = '#F43F5E';  // red — urgent
      else if (secondsLeft <= 300) timerEl.style.color = '#F59E0B';  // orange — warning
      else                         timerEl.style.color = '#0f172a';  // normal

      // When timer reaches 0, auto-submit
      if (secondsLeft <= 0) {
        clearInterval(timerInterval);
        examForm.submit();
        return;
      }

      secondsLeft--;
    }

    // Initialize display immediately, then run every second
    tick();
    var timerInterval = setInterval(tick, 1000);
  }


  /* ──────────────────────────────────────────────────────────
     2. ANSWER PROGRESS TRACKER
     Shows how many questions the student has answered.
  ────────────────────────────────────────────────────────── */

  const progressEl = document.getElementById('question-progress');

  if (progressEl && examForm) {

    const allRadios   = examForm.querySelectorAll('input[type="radio"]');
    const questionNames = new Set();
    allRadios.forEach(function(r) { questionNames.add(r.name); });
    const totalQuestions = questionNames.size;

    function updateProgress() {
      var answered = 0;
      questionNames.forEach(function(name) {
        if (examForm.querySelector('input[name="' + name + '"]:checked')) {
          answered++;
        }
      });

      var pct = totalQuestions > 0 ? Math.round((answered / totalQuestions) * 100) : 0;
      var isDone = answered === totalQuestions;

      // Update the progress display
      progressEl.innerHTML =
        '<div class="flex justify-between text-xs text-slate-400 mb-1.5">' +
          '<span>' + answered + '/' + totalQuestions + ' answered</span>' +
          '<span class="font-semibold ' + (isDone ? 'text-emerald-500' : 'text-cyan-500') + '">' + pct + '%</span>' +
        '</div>' +
        '<div style="height:5px; border-radius:99px; background:#e2e8f0; overflow:hidden;">' +
          '<div style="height:100%; border-radius:99px; width:' + pct + '%; background:' + (isDone ? '#10B981' : '#06B6D4') + '; transition:width 0.3s ease;"></div>' +
        '</div>' +
        (isDone ? '<p class="text-[10px] text-emerald-500 font-semibold mt-2 text-center">✓ All answered — ready to submit!</p>' : '');
    }

    // Update whenever a radio button is selected
    allRadios.forEach(function(radio) {
      radio.addEventListener('change', updateProgress);
    });

    // Initialize on page load
    updateProgress();
  }

});
