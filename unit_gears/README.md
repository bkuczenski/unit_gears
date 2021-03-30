# Gear Models
This folder contains work related to the gear models used in the TNC fishing gear study.

From the methodology document, the key formula for computing gear losses is:

$$ L_{g,s} = \frac{F_{g,s}}{\chi_g}\cdot \left(a_{g,s} + l_{g,s} + d_{g,s}\right ) $$

where $F_{g,s}$ is total catch (reported plus unreported plus discards) for gear of type *g* in a given segment *s*,
$\chi_g$ is the capture rate for gear type *g* (amount of catch for a unit of gear operation), and *a*, *l* and *d*
represent the mass of gear that is abandoned, lost, and discarded for each gear operation unit.

This formluation leaves a little bit out because it does not localize exactly where the mass of the gear is defined. This
is nominally defined in the *gear unit* $\ \mathbf{\mu}_g$, but that cancels out in the formulation, and so that
means the mass of the gear has to be folded into the capture rate.  Capture rate becomes a definition of "mass of fish caught
per mass of gear per unit of operation", and then *a*, *l*, and *d* can be pure loss fractions.

Let's try out how this works.  Let's say the mass of a characterized longline rig is 2,254 kg and includes 1,729 branchlines.
And let's say that during an 8-hour soak, 85% of hooks get hooked (C+U+D) with an average weight of 30 kg.  That's a catch of
1729 * 0.85 * 30 = 44090 kg.

MM's loss rate is 375 kg per 200 sets (leaving out abandoned and discarded).  That's 1.875 kg per set-- almost nothing!
That means the parameter *l* is 1.875 / 2254 = 0.00083.

Meanwhile, the *F* for those 200 sets is 8.82e6. We have $\frac{F}{\chi}\cdot l = 375$ which means
$\ \chi = \frac{F\cdot l}{375} = 19.52$ kg/kg/set.  That's 44090/2254.

So reformulating the methodology, $\chi$ is mass of catch per mass of gear per unspecified unit of operation, and a, l, and d are the
fractional loss of that mass of gear over the same unspecified unit of operation.

## Gear Loss Parameters

| Parameter | Dimension | Meaning |
|----|----|----|
|*m* | kg | Mass of a characterized unit of gear |
|*T* | operation unit | characterized unit of operation (set, hour, etc) |
|$\hat{\chi}$ | kg/op unit | Modified capture: total mass of catch per *T* |
|$\chi$ | 1/op unit | Nominal Capture Rate; $\hat{\chi}/m$ |
|*a* | fraction | Dimensionless abandonment fraction per *T* |
|*l* | fraction | Dimensionless loss fraction per *T* |
|*d* | fraction | Dimensionless discard fraction per *T* |
|$p_a$ | plastic fraction | Fraction of *a* that is plastic |
|$p_l$ | plastic fraction | Fraction of *l* that is plastic |
|$p_d$ | plastic fraction | Fraction of *d* that is plastic |

Gear Loss Equation:

$$ \bar{L}_g = \frac{L_{g,s}}{F_{g,s}} =
m_g\cdot \frac{ a_g\cdot p_{a,g} + l_g\cdot p_{l,g} + d_g\cdot p_{d,g}}{\hat{\chi}_g} $$

## Gear Loss Calculation

1. Required parameters for gear *g* include *m*, *T*, $\hat{\chi}$, *a*, *l*, *d*, $p_a$, $p_l$,
$p_d$.

2. Compute $\bar{L}_g$ for each gear type.

3. Multiply $\bar{L}_g$ by $F_{g,s}$ for each segment to determine the gear loss per segment.

