"One-pixel attack"

Imagine changing the value of one pixel in an image and the neural networks predict the image of a horse as 99% frog.

This is totally possible and is called as “one-pixel attack”.

One-pixel attack is a subset of the idea called “adversarial attacks” or “adversarial examples” where we can make a small modification that humans cannot detect to an image and make the neural network misclassify.

In regular adversarial attacks, we can modify any number of pixels by an incredibly small value.

In a one-pixel attack, we can only modify one pixel of the image by as much as we want.

The way we find the pixel whose modification and R, G, B value modification that leads to misclassification is figured out through an algorithm called “differential evolution”.

Differential evolution is similar to genetic algorithm. A few pixels are randomly selected as the parents. The parents mutate and produce “offspring” pixels. If the offspring can increase the loss function or decrease the prediction confidence, then they survive (survival of the fittest). Otherwise, they are discarded (elimination of the unfit).

Evolution is random mutation and non-random selection. We are likely to arrive at the optima, but not guaranteed.

Differential evolution (DE) is so powerful because unlike gradient descent you don’t need a differentiable function. You can apply DE on any function.

I have created a full lecture video of "one-pixel attack" on Vizuara Technologies Private Limited’s YouTube channel where I cover the following.

1. Review the seminal one-pixel attack paper published on arXiv by Su et al
2. Teach the concept behind one-pixel attack
3. Review differential evolution
4. Implement one-pixel attack in Google Colab (code shared in the video description)

Here is the link to the lecture: https://lnkd.in/gSQF4dMC

This lecture is part of the Explainable AI (XAI) lecture series.
