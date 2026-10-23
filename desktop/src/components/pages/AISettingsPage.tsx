import { motion } from 'framer-motion'
import {
  BrainCircuit, Sparkles, Bot, Server, Globe, Database, Cpu,
  ArrowRight, Info, Lightbulb, Shield, Activity, Calendar, MessageSquare,
} from 'lucide-react'
import { Card } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { PageHero } from '../ui/PageHero'
import type { SystemInfo } from '../../types'

const providers = [
  { id: 'openai', name: 'OpenAI', icon: <Sparkles className="w-6 h-6" />, description: 'GPT-4o, GPT-4o-mini — Best for general analysis and recommendations', models: ['gpt-4o', 'gpt-4o-mini'] },
  { id: 'gemini', name: 'Google Gemini', icon: <Bot className="w-6 h-6" />, description: 'Gemini 2.0 Flash, Pro — Fast and capable multimodal AI', models: ['gemini-2.0-flash', 'gemini-2.0-pro'] },
  { id: 'claude', name: 'Anthropic Claude', icon: <BrainCircuit className="w-6 h-6" />, description: 'Claude Sonnet, Haiku — Excellent for detailed technical analysis', models: ['claude-sonnet-4', 'claude-3-haiku'] },
  { id: 'openrouter', name: 'OpenRouter', icon: <Globe className="w-6 h-6" />, description: 'Unified API for 200+ models from all providers', models: ['any'] },
  { id: 'ollama', name: 'Ollama', icon: <Database className="w-6 h-6" />, description: 'Run models locally — fully private, no data leaves your PC', models: ['llama3', 'mistral', 'codellama'] },
  { id: 'lmstudio', name: 'LM Studio', icon: <Server className="w-6 h-6" />, description: 'Local model server with OpenAI-compatible API', models: ['any'] },
]

const plannedFeatures = [
  { icon: <Sparkles className="w-4 h-4" />, text: 'Real-time system health analysis with AI-driven recommendations' },
  { icon: <MessageSquare className="w-4 h-4" />, text: 'Natural language chat — ask questions about your PC in plain English' },
  { icon: <Activity className="w-4 h-4" />, text: 'Predictive bottleneck detection before they impact performance' },
  { icon: <Shield className="w-4 h-4" />, text: 'Security vulnerability scanning with AI-powered risk assessment' },
  { icon: <Calendar className="w-4 h-4" />, text: 'Scheduled AI audits with auto-generated optimization reports' },
  { icon: <Lightbulb className="w-4 h-4" />, text: 'Personalized tuning profiles learned from your usage patterns' },
]

export function AISettingsPage(_props: { systemInfo: SystemInfo | null }) {
  return (
    <motion.div initial="hidden" animate="show" className="page space-y-6">
            <PageHero
        title="AI Assistant"
        subtitle="Configure AI providers for intelligent system analysis"
        icon={<BrainCircuit size={19} />}
      />

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-5 rounded-2xl border border-yellow/30 bg-yellow-dim/30"
      >
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-yellow-dim text-yellow shrink-0">
            <Info className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-yellow mb-1">Coming Soon</h2>
            <p className="text-xs text-text-secondary leading-relaxed">
              Cloud AI features are currently under development. This page shows the planned architecture
              and provider integrations. Once released, you will be able to configure any supported AI
              provider to power Optinix's intelligent system analysis, optimization recommendations,
              and natural language assistance.
            </p>
          </div>
        </div>
      </motion.div>

      <motion.div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {providers.map((provider, i) => (
          <motion.div
            key={provider.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            whileHover={{ boxShadow: '0 0 24px rgba(124, 58, 237, 0.15)' }}
            className="relative p-5 rounded-2xl bg-surface-1 border border-border hover:border-accent/40 transition-all"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="p-3 rounded-xl bg-surface-2 text-accent">
                {provider.icon}
              </div>
              <Badge variant="warning">Coming Soon</Badge>
            </div>
            <h3 className="text-sm font-semibold text-text mb-1">{provider.name}</h3>
            <p className="text-xs text-text-secondary leading-relaxed mb-3">{provider.description}</p>
            <div className="flex flex-wrap gap-1.5">
              {provider.models.map(model => (
                <span
                  key={model}
                  className="px-2 py-0.5 rounded text-[10px] font-medium bg-surface-3 text-text-tertiary"
                >
                  {model}
                </span>
              ))}
            </div>
          </motion.div>
        ))}
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
        <Card padding="lg">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-accent-dim text-accent">
              <Cpu className="w-5 h-5" />
            </div>
            <h2 className="text-base font-semibold text-text">Architecture</h2>
          </div>

          <div className="mb-6 p-5 rounded-xl bg-surface-2/60 border border-border">
            <div className="flex items-center justify-center gap-3 flex-wrap text-xs">
              <div className="flex flex-col items-center gap-2 p-3 rounded-lg bg-surface-3">
                <MessageSquare className="w-5 h-5 text-accent" />
                <span className="text-text-secondary">You</span>
              </div>
              <ArrowRight className="w-4 h-4 text-text-tertiary" />
              <div className="flex flex-col items-center gap-2 p-3 rounded-lg bg-accent-dim/60 border border-accent/30">
                <BrainCircuit className="w-5 h-5 text-accent" />
                <span className="text-text-secondary">AI Layer</span>
              </div>
              <ArrowRight className="w-4 h-4 text-text-tertiary" />
              <div className="flex flex-col items-center gap-2 p-3 rounded-lg bg-surface-3">
                <Globe className="w-5 h-5 text-cyan" />
                <span className="text-text-secondary">Provider</span>
              </div>
              <ArrowRight className="w-4 h-4 text-text-tertiary" />
              <div className="flex flex-col items-center gap-2 p-3 rounded-lg bg-surface-3">
                <Sparkles className="w-5 h-5 text-green" />
                <span className="text-text-secondary">Response</span>
              </div>
            </div>
          </div>

          <p className="text-xs text-text-secondary leading-relaxed mb-5">
            Optinix uses a provider-agnostic AI architecture. Once configured, the AI assistant can
            analyze system health, provide optimization recommendations, answer questions about your PC,
            and more. All provider communication is handled through a unified abstraction layer,
            making it trivial to switch between providers without changing your workflow.
          </p>

          <h3 className="text-sm font-semibold text-text mb-3 flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-yellow" />
            Planned Features
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {plannedFeatures.map((feature, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-surface-2/50">
                <div className="text-accent shrink-0">{feature.icon}</div>
                <span className="text-xs text-text-secondary">{feature.text}</span>
              </div>
            ))}
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
