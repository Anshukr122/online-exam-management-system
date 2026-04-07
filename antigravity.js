/**
 * OEMS — Antigravity Feature
 * Powered by Matter.js physics engine
 *
 * VIVA EXPLANATION:
 * "Matter.js is a 2D physics engine for JavaScript. When the
 * user clicks 'Toggle Gravity', I convert each visible UI card
 * into a physics body. The engine then simulates gravity,
 * collisions, and mouse dragging. Toggling off restores the
 * original layout."
 *
 * KEY CONCEPTS USED:
 * - Engine: The physics simulation brain
 * - Bodies: Physical objects (rectangles matching our cards)
 * - Runner: Runs the simulation loop
 * - MouseConstraint: Allows drag-and-drop with mouse
 * - Events: Listen for each physics step to move DOM elements
 */

document.addEventListener('DOMContentLoaded', function() {

  // ── Get the toggle button. If it doesn't exist, stop here.
  const toggleBtn = document.getElementById('gravity-toggle');
  if (!toggleBtn) return;

  // ── Destructure Matter.js modules for cleaner code
  const { Engine, Runner, Bodies, Composite, Mouse, MouseConstraint, Events, Body } = Matter;

  // ── State variables
  let engine, runner;
  let isActive  = false;   // is physics currently running?
  let domBodies = [];      // stores { body, elem, w, h, origStyles }


  /* ──────────────────────────────────────────────────────────
     HELPER: Save original CSS styles of an element
     We need these to restore the layout when physics stops.
  ────────────────────────────────────────────────────────── */
  function saveStyles(el) {
    return {
      position:     el.style.position,
      left:         el.style.left,
      top:          el.style.top,
      width:        el.style.width,
      height:       el.style.height,
      margin:       el.style.margin,
      transform:    el.style.transform,
      zIndex:       el.style.zIndex,
      transition:   el.style.transition,
      pointerEvents: el.style.pointerEvents
    };
  }


  /* ──────────────────────────────────────────────────────────
     START PHYSICS
     1. Create the physics engine
     2. Add floor + wall boundaries
     3. Convert DOM elements to physics bodies
     4. Enable mouse drag
     5. Run the simulation
  ────────────────────────────────────────────────────────── */
  function startPhysics() {
    if (isActive) return;
    isActive = true;

    document.body.classList.add('physics-mode');
    updateToggleButton(true);

    // Create physics engine with gravity pointing down
    engine = Engine.create({ gravity: { x: 0, y: 2 } });

    const W = window.innerWidth;
    const H = window.innerHeight;

    // Static walls: invisible boundaries that elements bounce off
    const wallOptions = { isStatic: true, restitution: 0.4, friction: 0.3 };
    Composite.add(engine.world, [
      Bodies.rectangle(W / 2, H + 30,  W * 2, 60, wallOptions),  // floor
      Bodies.rectangle(-30,   H / 2,   60, H * 2, wallOptions),  // left wall
      Bodies.rectangle(W + 30, H / 2,  60, H * 2, wallOptions),  // right wall
      Bodies.rectangle(W / 2,  -30,    W * 2, 60, wallOptions),  // ceiling
    ]);

    // Find all elements that should fall
    const targets = document.querySelectorAll(
      '.glass, .glass-card, .stat-card, .physics-element, button:not(#gravity-toggle)'
    );

    const processed = new Set();

    targets.forEach(function(el) {
      // Skip duplicates and sidebar/navbar elements
      if (processed.has(el)) return;
      if (el.closest('#sidebar, .sidebar-element, .navbar-element')) return;

      const rect = el.getBoundingClientRect();
      if (rect.width < 20 || rect.height < 10) return;  // skip tiny elements

      processed.add(el);

      // Create a physics rectangle that matches the DOM element's size and position
      const body = Bodies.rectangle(
        rect.left + rect.width  / 2,   // center X
        rect.top  + rect.height / 2,   // center Y
        rect.width,
        rect.height,
        {
          restitution: 0.5,    // bounciness
          friction:    0.2,    // surface friction
          density:     0.003,  // mass (lighter = flies more)
          chamfer:     { radius: 4 }  // slightly rounded corners
        }
      );

      // Give each body a small random starting velocity for variety
      Body.setVelocity(body, {
        x: (Math.random() - 0.5) * 3,
        y: -Math.random() * 2
      });

      domBodies.push({
        body:       body,
        elem:       el,
        w:          rect.width,
        h:          rect.height,
        origStyles: saveStyles(el)
      });

      Composite.add(engine.world, body);
    });

    // Switch all elements to fixed positioning so we can move them with JS
    domBodies.forEach(function(item) {
      item.elem.style.position    = 'fixed';
      item.elem.style.width       = item.w + 'px';
      item.elem.style.height      = item.h + 'px';
      item.elem.style.margin      = '0';
      item.elem.style.transition  = 'none';
      item.elem.style.zIndex      = '9999';
      item.elem.style.left        = (item.body.position.x - item.w / 2) + 'px';
      item.elem.style.top         = (item.body.position.y - item.h / 2) + 'px';
      item.elem.style.transform   = '';
    });

    // Enable mouse dragging
    const mouse           = Mouse.create(document.body);
    const mouseConstraint = MouseConstraint.create(engine, {
      mouse: mouse,
      constraint: { stiffness: 0.18, damping: 0.1, render: { visible: false } }
    });
    // Keep normal page scrolling working while physics is active
    mouseConstraint.mouse.element.removeEventListener('mousewheel',     mouseConstraint.mouse.mousewheel);
    mouseConstraint.mouse.element.removeEventListener('DOMMouseScroll', mouseConstraint.mouse.mousewheel);
    Composite.add(engine.world, mouseConstraint);

    // Every physics step: move the DOM element to match the physics body
    Events.on(engine, 'afterUpdate', syncDOMWithPhysics);

    // Start the simulation
    runner = Runner.create();
    Runner.run(runner, engine);
  }


  /* ──────────────────────────────────────────────────────────
     SYNC DOM WITH PHYSICS
     Called every frame. Moves each HTML element to match
     where Matter.js says its physics body should be.
  ────────────────────────────────────────────────────────── */
  function syncDOMWithPhysics() {
    domBodies.forEach(function(item) {
      item.elem.style.left      = (item.body.position.x - item.w / 2) + 'px';
      item.elem.style.top       = (item.body.position.y - item.h / 2) + 'px';
      item.elem.style.transform = 'rotate(' + item.body.angle + 'rad)';
    });
  }


  /* ──────────────────────────────────────────────────────────
     STOP PHYSICS
     1. Stop the simulation
     2. Animate elements back to their original positions
     3. Restore original CSS styles
  ────────────────────────────────────────────────────────── */
  function stopPhysics() {
    if (!isActive) return;

    // Stop the engine
    Events.off(engine, 'afterUpdate', syncDOMWithPhysics);
    Runner.stop(runner);
    Engine.clear(engine);

    // Animate each element back to its original position
    domBodies.forEach(function(item) {
      item.elem.style.transition = 'left 0.45s cubic-bezier(0.4,0,0.2,1), top 0.45s cubic-bezier(0.4,0,0.2,1), transform 0.4s ease';
      item.elem.style.transform  = 'rotate(0deg)';

      // After animation finishes, fully restore original styles
      setTimeout(function() {
        var s = item.origStyles;
        item.elem.style.position     = s.position;
        item.elem.style.left         = s.left;
        item.elem.style.top          = s.top;
        item.elem.style.width        = s.width;
        item.elem.style.height       = s.height;
        item.elem.style.margin       = s.margin;
        item.elem.style.transform    = s.transform;
        item.elem.style.zIndex       = s.zIndex;
        item.elem.style.transition   = s.transition;
        item.elem.style.pointerEvents = s.pointerEvents;
      }, 460);
    });

    // Reset state
    domBodies = [];
    isActive  = false;
    document.body.classList.remove('physics-mode');
    updateToggleButton(false);
  }


  /* ──────────────────────────────────────────────────────────
     UPDATE TOGGLE BUTTON APPEARANCE
     Changes text and color to reflect current state.
  ────────────────────────────────────────────────────────── */
  function updateToggleButton(active) {
    if (active) {
      toggleBtn.innerHTML       = '<i class="fas fa-undo text-xs mr-1.5"></i> Restore Reality';
      toggleBtn.style.background = 'linear-gradient(135deg, #F43F5E, #F97316)';
      toggleBtn.style.boxShadow  = '0 3px 12px rgba(244,63,94,0.45)';
    } else {
      toggleBtn.innerHTML       = '<i class="fas fa-meteor text-xs mr-1.5"></i> Toggle Gravity';
      toggleBtn.style.background = 'linear-gradient(135deg, #6366F1, #8B5CF6)';
      toggleBtn.style.boxShadow  = '0 3px 12px rgba(99,102,241,0.4)';
    }
  }


  /* ──────────────────────────────────────────────────────────
     EVENT LISTENERS
  ────────────────────────────────────────────────────────── */

  // Toggle gravity on button click
  toggleBtn.addEventListener('click', function() {
    isActive ? stopPhysics() : startPhysics();
  });

  // Auto-stop if window is resized (layout changes)
  window.addEventListener('resize', function() {
    if (isActive) stopPhysics();
  });

});
