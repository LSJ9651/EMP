<template>
  <canvas ref="canvasRef" class="bg-canvas"></canvas>
  <div class="glow glow-top-right"></div>
  <div class="glow glow-bottom-left"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const canvasRef = ref(null)
let animationId = null
let particles = []
let ctx = null
let canvasWidth = 0
let canvasHeight = 0

class Particle {
  constructor() {
    this.reset()
  }

  reset() {
    this.x = Math.random() * canvasWidth
    this.y = Math.random() * canvasHeight
    this.size = Math.random() * 3 + 1
    this.speedX = (Math.random() - 0.5) * 0.6
    this.speedY = (Math.random() - 0.5) * 0.6
    this.opacity = Math.random() * 0.5 + 0.2
    this.pulse = Math.random() * Math.PI * 2
    this.pulseSpeed = Math.random() * 0.02 + 0.01
  }

  update() {
    this.pulse += this.pulseSpeed
    this.x += this.speedX
    this.y += this.speedY

    if (this.x < -10) this.x = canvasWidth + 10
    if (this.x > canvasWidth + 10) this.x = -10
    if (this.y < -10) this.y = canvasHeight + 10
    if (this.y > canvasHeight + 10) this.y = -10
  }

  draw() {
    const currentOpacity = this.opacity * (0.7 + 0.3 * Math.sin(this.pulse))
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(79, 140, 247, ${currentOpacity})`
    ctx.fill()

    // 光晕
    if (this.size > 2) {
      ctx.beginPath()
      ctx.arc(this.x, this.y, this.size * 3, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(79, 140, 247, ${currentOpacity * 0.1})`
      ctx.fill()
    }
  }
}

function initParticles() {
  const count = Math.min(70, Math.floor((canvasWidth * canvasHeight) / 18000))
  particles = Array.from({ length: count }, () => new Particle())
}

function drawLines() {
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x
      const dy = particles[i].y - particles[j].y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 150) {
        const alpha = 0.1 * (1 - dist / 150)
        ctx.beginPath()
        ctx.moveTo(particles[i].x, particles[i].y)
        ctx.lineTo(particles[j].x, particles[j].y)
        ctx.strokeStyle = `rgba(79, 140, 247, ${alpha})`
        ctx.lineWidth = 0.5
        ctx.stroke()
      }
    }
  }
}

function animate() {
  ctx.clearRect(0, 0, canvasWidth, canvasHeight)
  drawLines()
  particles.forEach(p => {
    p.update()
    p.draw()
  })
  animationId = requestAnimationFrame(animate)
}

function resizeCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  canvasWidth = window.innerWidth
  canvasHeight = window.innerHeight
  canvas.width = canvasWidth
  canvas.height = canvasHeight

  if (particles.length > 0) {
    initParticles()
  }
}

onMounted(() => {
  const canvas = canvasRef.value
  ctx = canvas.getContext('2d')
  resizeCanvas()
  initParticles()
  animate()
  window.addEventListener('resize', resizeCanvas)
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }
  window.removeEventListener('resize', resizeCanvas)
  particles = []
})
</script>

<style scoped>
.bg-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.glow {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}

.glow-top-right {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(79, 140, 247, 0.12) 0%, transparent 70%);
  top: -150px;
  right: -100px;
  animation: glowFloat1 8s ease-in-out infinite alternate;
}

.glow-bottom-left {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(108, 92, 231, 0.1) 0%, transparent 70%);
  bottom: -200px;
  left: -150px;
  animation: glowFloat2 10s ease-in-out infinite alternate;
}

@keyframes glowFloat1 {
  0% { transform: translate(0, 0) scale(1); }
  100% { transform: translate(30px, 30px) scale(1.1); }
}

@keyframes glowFloat2 {
  0% { transform: translate(0, 0) scale(1); }
  100% { transform: translate(-20px, -20px) scale(1.15); }
}
</style>
