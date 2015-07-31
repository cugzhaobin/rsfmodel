import numpy as np
from rsfmodel import rsf, staterelations, plot

model = rsf.Model()

# Set model initial conditions
model.mu0 = 0.6 # Friction initial (at the reference velocity)
model.a = 0.005 # Empirical coefficient for the direct effect
model.k = 1e-3 # Normalized System stiffness (friction/micron)
model.v = 1. # Initial slider velocity, generally is vlp(t=0)
model.vref = 1. # Reference velocity, generally vlp(t=0)

state1 = staterelations.DieterichState()
state1.b = 0.01  # Empirical coefficient for the evolution effect
state1.Dc = 10.  # Critical slip distance

state2 = staterelations.DieterichState()
state2.b = 0.001  # Empirical coefficient for the evolution effect
state2.Dc = 5.  # Critical slip distance

model.state_relations = [state1,state2] # Which state relation we want to use

# We want to solve for 40 seconds at 100Hz
model.time = np.arange(0,40.01,0.01)

# We want to slide at 1 um/s for 10 s, then at 10 um/s for 31
lp_velocity = np.ones_like(model.time)
lp_velocity[10*100:] = 10. # Velocity after 10 seconds is 10 um/s

# Set the model load point velocity, must be same shape as model.model_time
model.loadpoint_velocity = lp_velocity

# Run the model!
model.solve()

# Make the 2D phase plot
plot.phasePlot(model)

# Make a 3D phase plot
plot.phasePlot3D(model)

# Make a plot in displacement
plot.dispPlot(model)

# Make a plot in time
plot.timePlot(model)
