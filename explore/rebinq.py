import numpy as np
from numpy import linspace, mean, pi as π, sin, tan, arctan, radians, degrees, sqrt, arcsin

n = 54
make_λ = lambda n=n: linspace(6, 4, n)
make_θ = lambda θ, n=n: linspace(3/4*θ, 5/4*θ, n)
qz = lambda θ, δ, n=n: mean(4*π/make_λ(n)*sin(radians(make_θ(θ,n)+δ)))

def check_q(θ):
    θ_base = θ
    θ = radians(make_θ(θ_base))
    λ = make_λ()
    q = 4*π/λ*sin(θ)
    q_bar = mean(q)
    θ_bar = mean(θ)
    λ_bar = mean(λ)
    λinv_bar = 1/mean(1/λ)
    θinv_bar = arcsin(q_bar*λinv_bar/(4*π))
    #q_approx = 4*π/λ_bar * sin(θ_bar)
    q_approx = 4*π/λinv_bar * sin(θinv_bar)
    #print(f"θ={θ_base} <q>={q_bar:.3f} <θ>={degrees(θ_bar):.2f} <λ>={λ_bar:.2f} q'={q_approx:.3f} (err={100*(q_approx - q_bar)/q_bar:.2f}%)")
    print(f"θ={θ_base} <q>={q_bar:.3f} <θ>={degrees(θinv_bar):.2f} <λ>={λinv_bar:.2f} q'={q_approx:.3f} (err={100*(q_approx - q_bar)/q_bar:.2f}%)")

def check_offset(θ, δ):
    θ_base = θ
    θ = radians(make_θ(θ_base))
    λ = make_λ()
    offset = radians(δ)
    q = 4*π/λ*sin(θ)
    qp = 4*π/λ*sin(θ+offset)
    q_bar = mean(q)
    θ_bar = arcsin(q_bar*mean(λ)/(4*π)) # find θ consistent with <q>, <λ>
    λ_bar = 4*π/q_bar*sin(mean(θ)) # find λ consistent with <q>, <θ>
    λinv_bar = 1/mean(1/λ)
    θinv_bar = arcsin(q_bar*λinv_bar/(4*π))
    qp_bar = mean(qp)
    #qp_approx = q_bar + 4*π/mean(λ)*sin(offset)
    #qp_approx = 4*π/mean(λ)*sin(mean(θ) + offset) # bad
    #qp_approx = 4*π/λinv_bar*sin(mean(θ) + offset) # bad
    qp_approx = 4*π/λinv_bar*sin(θinv_bar + offset) # best
    #qp_approx = 4*π/mean(λ)*sin(θ_bar + offset)
    #qp_approx = 4*π/λ_bar*sin(mean(θ) + offset)
    print(f"offset θ={θ_base}{δ:+g}, q={q_bar:.3f} q'={qp_approx:.3f} (err={100*(qp_approx - qp_bar)/qp_bar:.2f}%)")
    #print(f"<λ>={mean(λ):.2f} 1/<1/λ>={λinv_bar:.2f} q,<θ>→λ={λ_bar:.2f}")
    #print(f"<θ>={degrees(mean(θ)):.3f} q,<λ>→θ={degrees(θ_bar):.2f} q,1/<1/λ>→θ={degrees(θinv_bar):.2f}")

def check_broadening(θ, Δθ, r12, l12=2000, l2s=300, sample=100, Δλoλ=0.005):
    θ_base = θ
    Δθ_base = Δθ
    broadening = radians(Δθ)
    θ = radians(make_θ(θ_base))
    λ = make_λ()
    s2 = sample*sin(θ)/(1 + (1+r12)*l2s/l12)
    s1 = s2*r12
    w, t = arctan(abs((s1+s2)/2/l12)), arctan(abs((s1-s2)/2/l12))
    Δθ = sqrt((w**2 + t**2)/6)
    #print(f"s1={min(s1):.3f}")

    q = 4*π/λ*sin(θ)
    Δq = q * sqrt(Δλoλ**2 + (Δθ/tan(θ))**2)
    Δqp = q * sqrt(Δλoλ**2 + ((Δθ+broadening)/tan(θ))**2)

    q_bar = mean(q)
    Δq_bar = sqrt(mean(Δq**2) + mean(q**2) - q_bar**2)
    Δqp_bar = sqrt(mean(Δqp**2) + mean(q**2) - q_bar**2)

    λinv_bar = 1/mean(1/λ)
    θ_bar = arcsin(q_bar*λinv_bar/(4*π))
    #θ_bar = mean(θ)
    #Δθ_bar = sqrt(mean(Δθ**2) + mean(θ**2) - θ_bar**2)
    #Δθ_bar = sqrt(mean(Δθ**2) + mean(θ**2) - mean(θ)**2)
    Δθ_bar = sqrt(mean(Δθ**2))
    #Δθ_bar = mean(Δθ)
    Δq_approx = sqrt(Δq_bar**2
                     + (q_bar/tan(θ_bar))**2 * (2*broadening*Δθ_bar + broadening**2))

    #Δq_approx = sqrt(Δq_bar**2
    #                 + mean(q**2 * (2*broadening * Δθ + broadening**2)/tan(θ)**2))

    print(f"broadening θ={θ_base} Δθ={degrees(Δθ_bar):.3f}{Δθ_base:+g} q={q_bar:.3f} Δq={Δq_bar:.5f} Δq'≈{Δq_approx:.5f} (err={100*(Δq_approx-Δqp_bar)/Δqp_bar:.2f}%)")
    #print(f"    q={q_bar:.3f} Δq={Δq_bar:.5f} Δq'={Δqp_bar:.5f} Δq'≈{Δq_approx:.5f}")
    #print(f"    <θ>={degrees(θ_bar):.3f}")
    def show_err(a_label,a,b_label,b):
        print(f"    {a_label}={a:.5f} {b_label}={b:.5f} err={100*(b-a)/a:0.2f}%")
    #show_err("<1/tan(θ)^2>", mean(1/tan(θ)**2), "1/tan(<θ>)^2", 1/tan(θ_bar)**2)
    #show_err("<θ/tan(θ)^2>", mean(θ/tan(θ)**2), "<θ>/tan(<θ>)^2", θ_bar/tan(θ_bar)**2)

def demo():
    """
    Generate q-bins with a range of θ,λ values in each bin. This uses a fixed
    wavelength range λ ∈ [4, 6] and corresponding θ ∈ [3/4 θ', 5/4 θ'], which in
    the small angle approximation gives q approximately constant. So the
    median λ is 5 and median θ is θ'.

    The following are computed::

        [q] = <q> = <4π/λ sin(θ)>
        [λ] = 1/<1/λ>
        [θ] = arcsin([q] [λ] / 4π)
        [Δq]² = <q √ {(Δλ/λ)² + (Δθ/tan θ)²}> + <q²> - <q>²
        [Δλ]² = <Δλ²>
        [Δθ]² = <Δθ²>
        [q'] = 4π/[λ] sin([θ] + δ)                     for θ-offset δ
        [Δq']² = [Δq]² + ([q]/tan[θ])² (2ω [Δθ] + ω²)  for sample broadening ω

    The result is an error in [q'] and [Δq'] < 1% over a wide range of angles
    and slits.

    The <q²> - <q>² term in [Δq] comes from the formula for variance in a
    mixture distribution, which averages the variances of the individual
    distributions and adds a spread term in case the means are not overlapping.
    See <https://en.wikipedia.org/wiki/Mixture_distribution#Moments>_.

    The sample broadening formula [Δq'] comes from substituting Δθ+ω for Δθ
    in [Δq] and expanding the square. By using [Δq]² to compute [Δq']², the
    spread term is automatically incorporated. This change may require updates
    to the fitting software, which compute [Δq'] from (θ,λ,Δθ,Δλ) directly.

    Note that the [Δλ] and [Δθ] terms do *not* represent the full width of the
    distributions. Since θ and λ are completely correlated based on the q value
    within the bin, Δq is smaller than expected from the full Δθ and Δλ, with
    a thin resolution window following the constant q curve on a θ-λ plot.

    A variety of formulae were investigated for an ideal <λ> and <θ> to store
    with the bin such that refl1d would be able to fit θ offset and sample
    broadening. The alternatives can be resurrected by selectively removing
    comments from the various code blocks.

    TODO: model beam intensity as a function of slit and wavelength
    """
    for θ in (0.01, 0.1, 0.2, 1, 5, 10, 15):
        print()
        #check_q(θ)
        check_offset(θ, 0.1)
        #check_broadening(θ, 0.02, r12=1)
        #check_broadening(θ, 0.2, r12=1)
        check_broadening(θ, 2, r12=1)
        #check_broadening(θ, 0.2, r12=10)
        #check_broadening(θ, -0.2, r12=1)

if __name__ == "__main__":
    demo()
